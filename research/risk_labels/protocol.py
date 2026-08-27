from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime, time
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig

CONFIG_VERSION = "next-session-volatility-risk-config-v1"
PROTOCOL_VERSION = "next-session-volatility-risk-v1"
LABEL_DATASET_VERSION = "next-session-volatility-risk-labels-v1"
OUTPUT_QUANTUM = Decimal("0.000000000001")


class RiskLabelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["next-session-volatility-risk-config-v1"] = CONFIG_VERSION
    protocol_version: Literal["next-session-volatility-risk-v1"] = PROTOCOL_VERSION
    market_timezone: str = Field(min_length=1, max_length=100)
    information_cutoff: time
    primary_outcome: Literal["next_normalized_abs_log_return"]
    trailing_volatility_sessions: int = Field(ge=2, le=252)
    trailing_volatility_ddof: Literal[0] = 0
    threshold_fit_split: Literal["train"] = "train"
    threshold_quantile: Decimal = Field(gt=0, lt=1)
    quantile_method: Literal["linear"] = "linear"
    label_comparison: Literal["greater_than_or_equal"] = "greater_than_or_equal"
    high_risk_label: Literal["HIGH_RISK"] = "HIGH_RISK"
    normal_label: Literal["NORMAL"] = "NORMAL"
    materialized_splits: tuple[Literal["train", "validation"], ...] = Field(
        min_length=2,
        max_length=2,
    )
    minimum_training_rows: int = Field(ge=1)
    minimum_training_rows_per_ticker: int = Field(ge=1)
    minimum_validation_rows_per_ticker: int = Field(ge=1)
    secondary_outcomes: tuple[str, ...] = Field(min_length=1)

    @field_validator("materialized_splits")
    @classmethod
    def validate_materialized_splits(
        cls, value: tuple[Literal["train", "validation"], ...]
    ) -> tuple[Literal["train", "validation"], ...]:
        if set(value) != {"train", "validation"}:
            raise ValueError("M2 must materialize train and validation only")
        return ("train", "validation")

    @field_validator("secondary_outcomes")
    @classmethod
    def validate_secondary_outcomes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = {
            "next_abs_log_return",
            "next_high_low_log_range",
            "next_parkinson_volatility",
        }
        if set(value) != expected:
            raise ValueError("secondary outcome contract does not match protocol v1")
        return (
            "next_abs_log_return",
            "next_high_low_log_range",
            "next_parkinson_volatility",
        )


def load_risk_label_config(path: Path) -> RiskLabelConfig:
    return RiskLabelConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_risk_label_dataset(
    config: RiskLabelConfig,
    market_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    _verify_market_dataset(market_dataset)
    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    if config.market_timezone != market_config.market_timezone:
        raise ValueError("risk-label and market-dataset timezones differ")

    benchmark_sessions = _benchmark_sessions(market_dataset)
    bars_by_ticker = _stock_bars(market_dataset, market_config)
    drafts: list[dict[str, object]] = []
    excluded = Counter()
    for instrument in market_config.universe:
        ticker_drafts, ticker_excluded = _build_ticker_drafts(
            ticker=instrument.ticker,
            bars=bars_by_ticker.get(instrument.ticker, {}),
            benchmark_sessions=benchmark_sessions,
            market_config=market_config,
            config=config,
        )
        drafts.extend(ticker_drafts)
        excluded.update(ticker_excluded)

    training_outcomes = [
        Decimal(str(row["continuous_risk_outcome"]))
        for row in drafts
        if row["split"] == config.threshold_fit_split
    ]
    if len(training_outcomes) < config.minimum_training_rows:
        raise ValueError(
            f"eligible training rows {len(training_outcomes)} are below "
            f"minimum {config.minimum_training_rows}"
        )
    per_ticker_split_counts = Counter(
        (str(row["ticker"]), str(row["split"])) for row in drafts
    )
    for instrument in market_config.universe:
        train_count = per_ticker_split_counts[(instrument.ticker, "train")]
        validation_count = per_ticker_split_counts[(instrument.ticker, "validation")]
        if train_count < config.minimum_training_rows_per_ticker:
            raise ValueError(
                f"{instrument.ticker} eligible training rows {train_count} are below "
                f"minimum {config.minimum_training_rows_per_ticker}"
            )
        if validation_count < config.minimum_validation_rows_per_ticker:
            raise ValueError(
                f"{instrument.ticker} eligible validation rows {validation_count} are below "
                f"minimum {config.minimum_validation_rows_per_ticker}"
            )
    threshold = linear_quantile(training_outcomes, config.threshold_quantile)
    protocol_config_sha256 = _hash(config.model_dump(mode="json"))
    threshold_payload = {
        "schema_version": "next-session-risk-threshold-v1",
        "protocol_version": config.protocol_version,
        "protocol_config_sha256": protocol_config_sha256,
        "market_dataset_sha256": market_dataset["sha256"],
        "fit_split": "train",
        "fit_period_end": market_config.train_end.isoformat(),
        "training_row_count": len(training_outcomes),
        "quantile": _format(config.threshold_quantile),
        "quantile_method": config.quantile_method,
        "threshold": _format(threshold),
        "validation_rows_used": 0,
        "sealed_test_rows_used": 0,
    }
    threshold_artifact = {
        **threshold_payload,
        "sha256": _hash(threshold_payload),
    }

    rows = []
    train_labels = Counter()
    for draft in sorted(drafts, key=lambda row: (str(row["feature_session"]), row["ticker"])):
        label = (
            config.high_risk_label
            if Decimal(str(draft["continuous_risk_outcome"])) >= threshold
            else config.normal_label
        )
        row = {
            **draft,
            "risk_threshold": _format(threshold),
            "risk_threshold_sha256": threshold_artifact["sha256"],
            "risk_label": label,
        }
        rows.append(row)
        if row["split"] == "train":
            train_labels[label] += 1

    dataset_content = {
        "schema_version": LABEL_DATASET_VERSION,
        "protocol_config": config.model_dump(mode="json"),
        "market_dataset_sha256": market_dataset["sha256"],
        "risk_threshold_sha256": threshold_artifact["sha256"],
        "protocol_config_sha256": protocol_config_sha256,
        "materialized_splits": list(config.materialized_splits),
        "sealed_test_rows_materialized": False,
        "rows": rows,
        "models_trained": False,
    }
    dataset = {**dataset_content, "sha256": _hash(dataset_content)}
    split_counts = Counter(str(row["split"]) for row in rows)
    train_total = sum(train_labels.values())
    report = {
        "report_version": "m2-risk-label-audit-v1",
        "passed": True,
        "protocol_version": config.protocol_version,
        "market_dataset_sha256": market_dataset["sha256"],
        "risk_label_dataset_sha256": dataset["sha256"],
        "risk_threshold_sha256": threshold_artifact["sha256"],
        "materialized_row_counts": dict(sorted(split_counts.items())),
        "excluded_row_counts": dict(sorted(excluded.items())),
        "training_label_counts": dict(sorted(train_labels.items())),
        "training_high_risk_prevalence": _format(
            Decimal(train_labels[config.high_risk_label]) / Decimal(train_total)
        ),
        "threshold_fit_split": "train",
        "threshold_quantile": _format(config.threshold_quantile),
        "threshold": _format(threshold),
        "validation_label_distribution_inspected": False,
        "sealed_test_rows_materialized": False,
        "sealed_test_outcomes_inspected": False,
        "models_trained": False,
        "manual_labels_used": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return dataset, threshold_artifact, report


def linear_quantile(values: list[Decimal], quantile: Decimal) -> Decimal:
    if not values:
        raise ValueError("quantile requires at least one value")
    if not Decimal(0) < quantile < Decimal(1):
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * quantile
    lower_index = int(position.to_integral_value(rounding=ROUND_FLOOR))
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - Decimal(lower_index)
    value = ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction
    return value.quantize(OUTPUT_QUANTUM, rounding=ROUND_HALF_EVEN)


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


def _build_ticker_drafts(
    *,
    ticker: str,
    bars: dict[date, dict[str, object]],
    benchmark_sessions: list[date],
    market_config: RiskMarketDatasetConfig,
    config: RiskLabelConfig,
) -> tuple[list[dict[str, object]], Counter[str]]:
    drafts = []
    excluded: Counter[str] = Counter()
    lookback = config.trailing_volatility_sessions
    materialized = set(config.materialized_splits)
    timezone = ZoneInfo(config.market_timezone)
    for index in range(lookback, len(benchmark_sessions) - 1):
        feature_session = benchmark_sessions[index]
        target_session = benchmark_sessions[index + 1]
        feature_split = market_config.split_for(feature_session)
        target_split = market_config.split_for(target_session)
        if feature_split == "test" or target_split == "test":
            excluded["sealed_test_not_materialized"] += 1
            continue
        if feature_split not in materialized or target_split != feature_split:
            excluded["outside_materialized_or_cross_split"] += 1
            continue
        history_sessions = benchmark_sessions[index - lookback : index + 1]
        if any(session not in bars for session in (*history_sessions, target_session)):
            excluded["missing_consecutive_market_bar"] += 1
            continue
        history_bars = [bars[session] for session in history_sessions]
        target_bar = bars[target_session]
        trailing_returns = [
            _log_ratio(
                Decimal(str(history_bars[position]["adjusted_close"])),
                Decimal(str(history_bars[position - 1]["adjusted_close"])),
            )
            for position in range(1, len(history_bars))
        ]
        trailing_scale = _population_std(trailing_returns)
        if trailing_scale <= 0:
            excluded["non_positive_trailing_volatility"] += 1
            continue
        current_close = Decimal(str(history_bars[-1]["adjusted_close"]))
        target_close = Decimal(str(target_bar["adjusted_close"]))
        next_log_return = _log_ratio(target_close, current_close)
        next_abs_log_return = abs(next_log_return)
        high_low_range = _log_ratio(
            Decimal(str(target_bar["high"])),
            Decimal(str(target_bar["low"])),
        )
        with localcontext() as context:
            context.prec = 34
            parkinson = abs(high_low_range) / (Decimal(4) * Decimal(2).ln()).sqrt()
        cutoff = datetime.combine(
            feature_session,
            config.information_cutoff,
            tzinfo=timezone,
        )
        cutoff_value = cutoff.isoformat()
        feature_state = {
            "ticker": ticker,
            "feature_session": feature_session.isoformat(),
            "information_cutoff": cutoff_value,
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
        drafts.append(
            {
                "ticker": ticker,
                "feature_session": feature_session.isoformat(),
                "information_cutoff": cutoff_value,
                "target_session": target_session.isoformat(),
                "split": feature_split,
                "feature_state_sha256": _hash(feature_state),
                "trailing_volatility_scale": _format(trailing_scale),
                "continuous_risk_outcome": _format(next_abs_log_return / trailing_scale),
                "next_abs_log_return": _format(next_abs_log_return),
                "next_high_low_log_range": _format(high_low_range),
                "next_parkinson_volatility": _format(parkinson),
            }
        )
    return drafts, excluded


def _verify_market_dataset(dataset: dict[str, object]) -> None:
    expected = dataset.get("sha256")
    content = {key: value for key, value in dataset.items() if key != "sha256"}
    if dataset.get("schema_version") != "risk-market-dataset-v1":
        raise ValueError("unexpected market dataset schema")
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError("market dataset SHA-256 mismatch")
    if dataset.get("models_trained") is not False:
        raise ValueError("M1 dataset model-training flag is invalid")
    if dataset.get("risk_labels_generated") is not False:
        raise ValueError("M1 dataset risk-label flag is invalid")
    if dataset.get("sealed_test_outcomes_inspected") is not False:
        raise ValueError("M1 dataset sealed-test flag is invalid")


def _benchmark_sessions(dataset: dict[str, object]) -> list[date]:
    rows = dataset.get("benchmark_rows")
    if not isinstance(rows, list):
        raise TypeError("market dataset benchmark_rows must be a list")
    sessions = [date.fromisoformat(str(row["date"])) for row in rows]
    if sessions != sorted(set(sessions)):
        raise ValueError("benchmark sessions must be unique and ordered")
    return sessions


def _stock_bars(
    dataset: dict[str, object], market_config: RiskMarketDatasetConfig
) -> dict[str, dict[date, dict[str, object]]]:
    rows = dataset.get("stock_rows")
    if not isinstance(rows, list):
        raise TypeError("market dataset stock_rows must be a list")
    allowed = {instrument.ticker for instrument in market_config.universe}
    output: dict[str, dict[date, dict[str, object]]] = {ticker: {} for ticker in allowed}
    for raw in rows:
        if not isinstance(raw, dict):
            raise TypeError("stock row must be an object")
        ticker = str(raw["ticker"])
        if ticker not in allowed:
            continue
        trading_date = date.fromisoformat(str(raw["trading_date"]))
        if trading_date in output[ticker]:
            raise ValueError(f"duplicate stock row: {ticker} {trading_date}")
        output[ticker][trading_date] = raw
    return output


def _population_std(values: list[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = 34
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
        return variance.sqrt()


def _log_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if numerator <= 0 or denominator <= 0:
        raise ValueError("log-return inputs must be positive")
    with localcontext() as context:
        context.prec = 34
        return (numerator / denominator).ln()


def _format(value: Decimal) -> str:
    return format(value.quantize(OUTPUT_QUANTUM, rounding=ROUND_HALF_EVEN), "f")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
