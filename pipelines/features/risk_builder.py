from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, time
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig

CONFIG_VERSION = "risk-feature-config-v1"
PIPELINE_VERSION = "risk-features-v1"
DATASET_VERSION = "risk-feature-dataset-v1"
OUTPUT_QUANTUM = Decimal("0.000000000001")

FEATURE_NAMES = (
    "return_log_1",
    "return_log_5",
    "return_log_10",
    "return_log_20",
    "overnight_gap_log_1",
    "close_ma_deviation_5",
    "close_ma_deviation_20",
    "volume_log_change_1p_1",
    "volume_zscore_20",
    "zero_volume_flag",
    "volatility_log_return_5",
    "volatility_log_return_20",
    "high_low_log_range_1",
    "atr_14_normalized",
    "parkinson_mean_5",
    "rsi_14",
    "macd_12_26_normalized",
    "macd_signal_9_normalized",
    "benchmark_return_log_1",
    "benchmark_return_log_20",
    "benchmark_volatility_log_return_20",
    "stock_minus_benchmark_return_log_1",
    "benchmark_drawdown_20",
)


class RiskFeatureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-feature-config-v1"] = CONFIG_VERSION
    pipeline_version: Literal["risk-features-v1"] = PIPELINE_VERSION
    market_timezone: str = Field(min_length=1, max_length=100)
    information_cutoff: time
    materialized_splits: tuple[Literal["train", "validation"], ...] = Field(
        min_length=2,
        max_length=2,
    )
    required_consecutive_sessions: int = Field(ge=35, le=252)
    return_windows: tuple[int, ...]
    moving_average_windows: tuple[int, ...]
    volume_zscore_window: int
    volatility_windows: tuple[int, ...]
    atr_window: int
    parkinson_window: int
    rsi_window: int
    macd_fast_span: int
    macd_slow_span: int
    macd_signal_span: int
    benchmark_return_windows: tuple[int, ...]
    benchmark_volatility_window: int
    benchmark_drawdown_window: int
    minimum_training_rows_per_ticker: int = Field(ge=1)
    minimum_validation_rows_per_ticker: int = Field(ge=1)
    feature_names: tuple[str, ...]

    @field_validator("materialized_splits")
    @classmethod
    def validate_materialized_splits(
        cls, value: tuple[Literal["train", "validation"], ...]
    ) -> tuple[Literal["train", "validation"], ...]:
        if set(value) != {"train", "validation"}:
            raise ValueError("M3 must materialize train and validation only")
        return ("train", "validation")

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(value) != FEATURE_NAMES:
            raise ValueError("feature_names must match the risk-features-v1 contract")
        return FEATURE_NAMES

    @model_validator(mode="after")
    def validate_formula_contract(self) -> RiskFeatureConfig:
        expected = {
            "return_windows": (1, 5, 10, 20),
            "moving_average_windows": (5, 20),
            "volume_zscore_window": 20,
            "volatility_windows": (5, 20),
            "atr_window": 14,
            "parkinson_window": 5,
            "rsi_window": 14,
            "macd_fast_span": 12,
            "macd_slow_span": 26,
            "macd_signal_span": 9,
            "benchmark_return_windows": (1, 20),
            "benchmark_volatility_window": 20,
            "benchmark_drawdown_window": 20,
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(f"{field_name} does not match risk-features-v1")
        if self.required_consecutive_sessions < 35:
            raise ValueError("risk-features-v1 requires at least 35 consecutive sessions")
        return self


def load_risk_feature_config(path: Path) -> RiskFeatureConfig:
    return RiskFeatureConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_risk_feature_dataset(
    config: RiskFeatureConfig,
    market_dataset: dict[str, object],
    label_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    _verify_inputs(market_dataset, label_dataset)
    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    if config.market_timezone != market_config.market_timezone:
        raise ValueError("feature and market timezones differ")

    benchmark_sessions, benchmark_prices = _benchmark_market(market_dataset)
    benchmark_index = {session: index for index, session in enumerate(benchmark_sessions)}
    stock_bars = _stock_market(market_dataset, market_config)
    label_rows = _label_rows(label_dataset)
    output_rows = []
    excluded = Counter()
    per_ticker_split_counts = Counter()
    for label_row in label_rows:
        ticker = str(label_row["ticker"])
        feature_session = date.fromisoformat(str(label_row["feature_session"]))
        target_session = date.fromisoformat(str(label_row["target_session"]))
        split = str(label_row["split"])
        if split not in config.materialized_splits:
            raise ValueError("label dataset contains a non-materialized split")
        index = benchmark_index.get(feature_session)
        if index is None or index + 1 >= len(benchmark_sessions):
            excluded["missing_benchmark_feature_or_target_session"] += 1
            continue
        if str(label_row["target_session"]) != benchmark_sessions[index + 1].isoformat():
            raise ValueError(f"label target is not the next benchmark session: {ticker}")
        if (
            market_config.split_for(feature_session) != split
            or market_config.split_for(target_session) != split
        ):
            raise ValueError(f"label split does not contain feature and target: {ticker}")
        cutoff = datetime.fromisoformat(str(label_row["information_cutoff"]))
        if cutoff.tzinfo is None:
            raise ValueError(f"label information cutoff lacks timezone: {ticker}")
        local_cutoff = cutoff.astimezone(ZoneInfo(config.market_timezone))
        if (
            local_cutoff.date() != feature_session
            or local_cutoff.time().replace(tzinfo=None) != config.information_cutoff
        ):
            raise ValueError(f"label information cutoff mismatch: {ticker}")
        start = index - config.required_consecutive_sessions + 1
        if start < 0:
            excluded["insufficient_feature_warmup"] += 1
            continue
        history_sessions = benchmark_sessions[start : index + 1]
        ticker_bars = stock_bars.get(ticker, {})
        if any(session not in ticker_bars for session in history_sessions):
            excluded["missing_consecutive_feature_bar"] += 1
            continue
        history_bars = [ticker_bars[session] for session in history_sessions]
        benchmark_history = benchmark_prices[start : index + 1]
        _verify_m2_feature_state(label_row, history_bars[-21:])
        features = _calculate_features(history_bars, benchmark_history, config)
        if tuple(features) != FEATURE_NAMES:
            raise ValueError("feature builder output order does not match contract")
        if any(value is None for value in features.values()):
            excluded["null_feature_value"] += 1
            continue
        if any(not math.isfinite(float(value)) for value in features.values()):
            excluded["non_finite_feature_value"] += 1
            continue
        feature_payload = {
            "ticker": ticker,
            "feature_session": feature_session.isoformat(),
            "information_cutoff": label_row["information_cutoff"],
            "features": features,
        }
        target_payload = {
            "target_session": label_row["target_session"],
            "continuous_risk_outcome": label_row["continuous_risk_outcome"],
            "next_abs_log_return": label_row["next_abs_log_return"],
            "next_high_low_log_range": label_row["next_high_low_log_range"],
            "next_parkinson_volatility": label_row["next_parkinson_volatility"],
            "risk_label": label_row["risk_label"],
            "risk_threshold_sha256": label_row["risk_threshold_sha256"],
        }
        output_rows.append(
            {
                **feature_payload,
                "split": split,
                "feature_values_sha256": _hash(feature_payload),
                "label_row_sha256": _hash(label_row),
                "target": target_payload,
            }
        )
        per_ticker_split_counts[(ticker, split)] += 1

    for instrument in market_config.universe:
        train_count = per_ticker_split_counts[(instrument.ticker, "train")]
        validation_count = per_ticker_split_counts[(instrument.ticker, "validation")]
        if train_count < config.minimum_training_rows_per_ticker:
            raise ValueError(
                f"{instrument.ticker} feature training rows {train_count} are below "
                f"minimum {config.minimum_training_rows_per_ticker}"
            )
        if validation_count < config.minimum_validation_rows_per_ticker:
            raise ValueError(
                f"{instrument.ticker} feature validation rows {validation_count} are below "
                f"minimum {config.minimum_validation_rows_per_ticker}"
            )

    ordered_rows = sorted(
        output_rows,
        key=lambda row: (str(row["feature_session"]), str(row["ticker"])),
    )
    config_sha256 = _hash(config.model_dump(mode="json"))
    content = {
        "schema_version": DATASET_VERSION,
        "pipeline_version": config.pipeline_version,
        "config": config.model_dump(mode="json"),
        "config_sha256": config_sha256,
        "market_dataset_sha256": market_dataset["sha256"],
        "risk_label_dataset_sha256": label_dataset["sha256"],
        "materialized_splits": list(config.materialized_splits),
        "sealed_test_features_materialized": False,
        "preprocessing_fitted": False,
        "models_trained": False,
        "rows": ordered_rows,
    }
    dataset = {**content, "sha256": _hash(content)}
    split_counts = Counter(str(row["split"]) for row in ordered_rows)
    report = {
        "report_version": "m3-risk-feature-audit-v1",
        "passed": True,
        "pipeline_version": config.pipeline_version,
        "market_dataset_sha256": market_dataset["sha256"],
        "risk_label_dataset_sha256": label_dataset["sha256"],
        "risk_feature_dataset_sha256": dataset["sha256"],
        "config_sha256": config_sha256,
        "feature_names": list(FEATURE_NAMES),
        "feature_count": len(FEATURE_NAMES),
        "materialized_row_counts": dict(sorted(split_counts.items())),
        "excluded_row_counts": dict(sorted(excluded.items())),
        "null_feature_value_count": 0,
        "validation_label_distribution_inspected": False,
        "sealed_test_features_materialized": False,
        "sealed_test_outcomes_inspected": False,
        "preprocessing_fitted": False,
        "models_trained": False,
        "manual_labels_used": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return dataset, report


def write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise FileExistsError(f"refusing to overwrite a different immutable file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _calculate_features(
    bars: list[dict[str, object]],
    benchmark_prices: list[Decimal],
    config: RiskFeatureConfig,
) -> dict[str, float | int | None]:
    adjusted = [Decimal(str(bar["adjusted_close"])) for bar in bars]
    raw_closes = [Decimal(str(bar["close"])) for bar in bars]
    volumes = [Decimal(str(bar["volume"])) for bar in bars]
    benchmark_returns = _returns(benchmark_prices, 20)
    stock_return_1 = _log_ratio(adjusted[-1], adjusted[-2])
    benchmark_return_1 = _log_ratio(benchmark_prices[-1], benchmark_prices[-2])
    macd, signal = _macd(adjusted, config)
    current_close = adjusted[-1]
    features: dict[str, float | int | None] = {
        "return_log_1": _number(stock_return_1),
        "return_log_5": _number(_log_ratio(adjusted[-1], adjusted[-6])),
        "return_log_10": _number(_log_ratio(adjusted[-1], adjusted[-11])),
        "return_log_20": _number(_log_ratio(adjusted[-1], adjusted[-21])),
        "overnight_gap_log_1": _number(
            _log_ratio(Decimal(str(bars[-1]["open"])), raw_closes[-2])
        ),
        "close_ma_deviation_5": _number(current_close / _mean(adjusted[-5:]) - 1),
        "close_ma_deviation_20": _number(current_close / _mean(adjusted[-20:]) - 1),
        "volume_log_change_1p_1": _number(
            (volumes[-1] + 1).ln() - (volumes[-2] + 1).ln()
        ),
        "volume_zscore_20": _number(_zscore(volumes[-20:])),
        "zero_volume_flag": int(volumes[-1] == 0),
        "volatility_log_return_5": _number(_population_std(_returns(adjusted, 5))),
        "volatility_log_return_20": _number(_population_std(_returns(adjusted, 20))),
        "high_low_log_range_1": _number(
            _log_ratio(Decimal(str(bars[-1]["high"])), Decimal(str(bars[-1]["low"])))
        ),
        "atr_14_normalized": _number(_atr_normalized(bars, config.atr_window)),
        "parkinson_mean_5": _number(_parkinson_mean(bars, config.parkinson_window)),
        "rsi_14": _number(_rsi(adjusted, config.rsi_window)),
        "macd_12_26_normalized": _number(macd / current_close),
        "macd_signal_9_normalized": _number(signal / current_close),
        "benchmark_return_log_1": _number(benchmark_return_1),
        "benchmark_return_log_20": _number(
            _log_ratio(benchmark_prices[-1], benchmark_prices[-21])
        ),
        "benchmark_volatility_log_return_20": _number(
            _population_std(benchmark_returns)
        ),
        "stock_minus_benchmark_return_log_1": _number(
            stock_return_1 - benchmark_return_1
        ),
        "benchmark_drawdown_20": _number(
            benchmark_prices[-1] / max(benchmark_prices[-20:]) - 1
        ),
    }
    return features


def _verify_inputs(
    market_dataset: dict[str, object], label_dataset: dict[str, object]
) -> None:
    _verify_hash(market_dataset, "market dataset")
    _verify_hash(label_dataset, "risk-label dataset")
    if market_dataset.get("schema_version") != "risk-market-dataset-v1":
        raise ValueError("unexpected market dataset schema")
    if label_dataset.get("schema_version") != "next-session-volatility-risk-labels-v1":
        raise ValueError("unexpected risk-label dataset schema")
    if label_dataset.get("market_dataset_sha256") != market_dataset.get("sha256"):
        raise ValueError("risk-label and market dataset lineage mismatch")
    if label_dataset.get("sealed_test_rows_materialized") is not False:
        raise ValueError("M3 refuses a label dataset with materialized sealed test")
    if label_dataset.get("models_trained") is not False:
        raise ValueError("M3 input model-training flag is invalid")


def _verify_hash(payload: dict[str, object], name: str) -> None:
    expected = payload.get("sha256")
    content = {key: value for key, value in payload.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError(f"{name} SHA-256 mismatch")


def _benchmark_market(
    market_dataset: dict[str, object],
) -> tuple[list[date], list[Decimal]]:
    rows = market_dataset.get("benchmark_rows")
    if not isinstance(rows, list):
        raise TypeError("benchmark_rows must be a list")
    sessions = [date.fromisoformat(str(row["date"])) for row in rows]
    prices = [Decimal(str(row["price"])) for row in rows]
    if sessions != sorted(set(sessions)):
        raise ValueError("benchmark sessions must be unique and ordered")
    return sessions, prices


def _stock_market(
    market_dataset: dict[str, object], market_config: RiskMarketDatasetConfig
) -> dict[str, dict[date, dict[str, object]]]:
    rows = market_dataset.get("stock_rows")
    if not isinstance(rows, list):
        raise TypeError("stock_rows must be a list")
    allowed = {instrument.ticker for instrument in market_config.universe}
    output: dict[str, dict[date, dict[str, object]]] = {ticker: {} for ticker in allowed}
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("stock row must be an object")
        ticker = str(row["ticker"])
        if ticker not in allowed:
            continue
        trading_date = date.fromisoformat(str(row["trading_date"]))
        if trading_date in output[ticker]:
            raise ValueError(f"duplicate stock row: {ticker} {trading_date}")
        output[ticker][trading_date] = row
    return output


def _label_rows(label_dataset: dict[str, object]) -> list[dict[str, object]]:
    rows = label_dataset.get("rows")
    if not isinstance(rows, list):
        raise TypeError("risk-label rows must be a list")
    seen = set()
    output = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("risk-label row must be an object")
        identity = (str(row["ticker"]), str(row["feature_session"]))
        if identity in seen:
            raise ValueError(f"duplicate risk-label row: {identity}")
        seen.add(identity)
        output.append(row)
    return output


def _verify_m2_feature_state(
    label_row: dict[str, object], history_bars: list[dict[str, object]]
) -> None:
    state = {
        "ticker": label_row["ticker"],
        "feature_session": label_row["feature_session"],
        "information_cutoff": label_row["information_cutoff"],
        "history": [
            {
                "trading_date": bar["trading_date"],
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "adjusted_close": bar["adjusted_close"],
                "volume": bar["volume"],
            }
            for bar in history_bars
        ],
    }
    if _hash(state) != label_row.get("feature_state_sha256"):
        raise ValueError("M2 feature-state lineage mismatch")


def _returns(values: list[Decimal], window: int) -> list[Decimal]:
    return [
        _log_ratio(values[index], values[index - 1])
        for index in range(len(values) - window, len(values))
    ]


def _atr_normalized(bars: list[dict[str, object]], window: int) -> Decimal:
    ranges = []
    for index in range(len(bars) - window, len(bars)):
        high = Decimal(str(bars[index]["high"]))
        low = Decimal(str(bars[index]["low"]))
        previous_close = Decimal(str(bars[index - 1]["close"]))
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return _mean(ranges) / Decimal(str(bars[-1]["close"]))


def _parkinson_mean(bars: list[dict[str, object]], window: int) -> Decimal:
    with localcontext() as context:
        context.prec = 34
        denominator = (Decimal(4) * Decimal(2).ln()).sqrt()
        values = [
            abs(
                _log_ratio(
                    Decimal(str(bar["high"])),
                    Decimal(str(bar["low"])),
                )
            )
            / denominator
            for bar in bars[-window:]
        ]
        return _mean(values)


def _rsi(closes: list[Decimal], window: int) -> Decimal:
    changes = [
        closes[index] - closes[index - 1]
        for index in range(len(closes) - window, len(closes))
    ]
    average_gain = _mean([max(change, Decimal(0)) for change in changes])
    average_loss = _mean([max(-change, Decimal(0)) for change in changes])
    if average_gain == average_loss == 0:
        return Decimal(50)
    if average_loss == 0:
        return Decimal(100)
    relative_strength = average_gain / average_loss
    return Decimal(100) - Decimal(100) / (Decimal(1) + relative_strength)


def _macd(closes: list[Decimal], config: RiskFeatureConfig) -> tuple[Decimal, Decimal]:
    fast = _ema(closes, config.macd_fast_span)
    slow = _ema(closes, config.macd_slow_span)
    macd = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow, strict=True)]
    signal = _ema(macd, config.macd_signal_span)
    return macd[-1], signal[-1]


def _ema(values: list[Decimal], span: int) -> list[Decimal]:
    alpha = Decimal(2) / Decimal(span + 1)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (Decimal(1) - alpha) * output[-1])
    return output


def _zscore(values: list[Decimal]) -> Decimal:
    standard_deviation = _population_std(values)
    if standard_deviation == 0:
        return Decimal(0)
    return (values[-1] - _mean(values)) / standard_deviation


def _population_std(values: list[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = 34
        mean = _mean(values)
        variance = _mean([(value - mean) ** 2 for value in values])
        return variance.sqrt()


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _log_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if numerator <= 0 or denominator <= 0:
        raise ValueError("log-ratio inputs must be positive")
    with localcontext() as context:
        context.prec = 34
        return (numerator / denominator).ln()


def _number(value: Decimal) -> float:
    quantized = value.quantize(OUTPUT_QUANTUM, rounding=ROUND_HALF_EVEN)
    return 0.0 if quantized == 0 else float(quantized)


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
