from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

from pipelines.features.risk_builder import (
    FEATURE_NAMES,
    OUTPUT_QUANTUM,
    RiskFeatureConfig,
    _calculate_features,
)
from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    canonical_config_sha256,
)

DATASET_VERSION = "final-volatility-surprise-dataset-v1"
REPORT_VERSION = "f2-final-study-dataset-audit-v1"


def build_final_study_dataset(
    protocol: FinalStudyProtocolConfig,
    feature_config: RiskFeatureConfig,
    market_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Build the F2 market-only dataset without fitting preprocessing or models."""
    _verify_market_dataset(protocol, market_dataset)
    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    _verify_contracts(protocol, feature_config, market_config)

    benchmark_sessions, benchmark_prices = _benchmark_market(market_dataset)
    stock_bars = _stock_market(market_dataset, market_config)
    study_start = min(fold.train_start for fold in protocol.outer_evaluation.folds)
    study_end = max(fold.evaluation_end for fold in protocol.outer_evaluation.folds)
    feature_config_sha256 = _hash(feature_config.model_dump(mode="json"))
    protocol_sha256 = canonical_config_sha256(protocol)
    minimum_scale = Decimal(str(protocol.primary_target.minimum_denominator_exclusive))
    timezone = ZoneInfo(feature_config.market_timezone)
    systematic_missing_sessions = _systematic_missing_stock_sessions(
        benchmark_sessions,
        stock_bars,
        study_start,
        study_end,
    )

    output_rows: list[dict[str, object]] = []
    excluded: Counter[str] = Counter()
    excluded_by_ticker: Counter[tuple[str, str]] = Counter()
    exclusion_date_bounds: dict[str, tuple[date, date]] = {}
    candidate_by_ticker: Counter[str] = Counter()
    candidate_count = 0
    for ticker in sorted(stock_bars):
        ticker_bars = stock_bars[ticker]
        for index, feature_session in enumerate(benchmark_sessions):
            if not study_start <= feature_session <= study_end:
                continue
            candidate_count += 1
            candidate_by_ticker[ticker] += 1
            if index + 1 >= len(benchmark_sessions):
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "missing_next_benchmark_session",
                    ticker,
                    feature_session,
                )
                continue
            target_session = benchmark_sessions[index + 1]
            if target_session > study_end:
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "target_session_after_study_end",
                    ticker,
                    feature_session,
                )
                continue
            start = index - feature_config.required_consecutive_sessions + 1
            if start < 0:
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "insufficient_feature_warmup",
                    ticker,
                    feature_session,
                )
                continue
            history_sessions = benchmark_sessions[start : index + 1]
            missing_history = [
                session for session in history_sessions if session not in ticker_bars
            ]
            if missing_history:
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "missing_consecutive_feature_bar",
                    ticker,
                    feature_session,
                )
                continue
            if target_session not in ticker_bars:
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "missing_immediate_target_bar",
                    ticker,
                    feature_session,
                )
                continue

            history_bars = [ticker_bars[session] for session in history_sessions]
            target_bar = ticker_bars[target_session]
            benchmark_history = benchmark_prices[start : index + 1]
            try:
                features = _calculate_features(history_bars, benchmark_history, feature_config)
                target = _calculate_target(
                    history_bars,
                    target_bar,
                    protocol.primary_target.name,
                    minimum_scale,
                )
            except (ArithmeticError, ValueError):
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "invalid_numeric_input",
                    ticker,
                    feature_session,
                )
                continue
            if target is None:
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "near_zero_or_non_finite_trailing_volatility",
                    ticker,
                    feature_session,
                )
                continue
            if tuple(features) != FEATURE_NAMES:
                raise ValueError("feature builder output order drifted from risk-features-v1")
            if any(value is None or not math.isfinite(float(value)) for value in features.values()):
                _record_exclusion(
                    excluded,
                    excluded_by_ticker,
                    exclusion_date_bounds,
                    "null_or_non_finite_feature",
                    ticker,
                    feature_session,
                )
                continue

            information_cutoff = datetime.combine(
                feature_session,
                feature_config.information_cutoff,
                tzinfo=timezone,
            ).isoformat()
            feature_payload = {
                "ticker": ticker,
                "feature_session": feature_session.isoformat(),
                "information_cutoff": information_cutoff,
                "features": features,
            }
            source_lineage = {
                "market_dataset_sha256": market_dataset["sha256"],
                "benchmark_snapshot_sha256": market_dataset["benchmark_snapshot_sha256"],
                "f1_protocol_config_sha256": protocol_sha256,
                "feature_config_sha256": feature_config_sha256,
                "feature_pipeline_version": feature_config.pipeline_version,
            }
            row_content = {
                **feature_payload,
                "target_session": target_session.isoformat(),
                "feature_values_sha256": _hash(feature_payload),
                "target": target,
                "source_lineage": source_lineage,
            }
            output_rows.append({**row_content, "row_sha256": _hash(row_content)})

    ordered_rows = sorted(
        output_rows,
        key=lambda row: (str(row["feature_session"]), str(row["ticker"])),
    )
    _verify_unique_rows(ordered_rows)
    content = {
        "schema_version": DATASET_VERSION,
        "dataset_version": DATASET_VERSION,
        "target_version": protocol.primary_target.name,
        "feature_pipeline_version": feature_config.pipeline_version,
        "f1_protocol_config_sha256": protocol_sha256,
        "feature_config_sha256": feature_config_sha256,
        "market_dataset_sha256": market_dataset["sha256"],
        "benchmark_snapshot_sha256": market_dataset["benchmark_snapshot_sha256"],
        "study_start": study_start.isoformat(),
        "study_end": study_end.isoformat(),
        "preprocessing_fitted": False,
        "models_trained": False,
        "binary_labels_materialized": False,
        "rows": ordered_rows,
    }
    dataset = {**content, "sha256": _hash(content)}
    report = _build_report(
        protocol=protocol,
        dataset=dataset,
        rows=ordered_rows,
        candidate_count=candidate_count,
        candidate_by_ticker=candidate_by_ticker,
        excluded=excluded,
        excluded_by_ticker=excluded_by_ticker,
        exclusion_date_bounds=exclusion_date_bounds,
        systematic_missing_sessions=systematic_missing_sessions,
    )
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


def _calculate_target(
    history_bars: list[dict[str, object]],
    target_bar: dict[str, object],
    target_version: str,
    minimum_scale: Decimal,
) -> dict[str, object] | None:
    adjusted = [Decimal(str(bar["adjusted_close"])) for bar in history_bars[-21:]]
    returns = [
        _log_ratio(adjusted[index], adjusted[index - 1])
        for index in range(1, len(adjusted))
    ]
    if len(returns) != 20:
        raise ValueError("primary target requires exactly 20 trailing returns")
    scale = _population_std(returns)
    if not scale.is_finite() or scale <= minimum_scale:
        return None
    current_close = adjusted[-1]
    target_close = Decimal(str(target_bar["adjusted_close"]))
    next_abs = abs(_log_ratio(target_close, current_close))
    next_range = abs(
        _log_ratio(
            Decimal(str(target_bar["high"])),
            Decimal(str(target_bar["low"])),
        )
    )
    with localcontext() as context:
        context.prec = 34
        parkinson = next_range / (Decimal(4) * Decimal(2).ln()).sqrt()
    primary = next_abs / scale
    values = (scale, next_abs, next_range, parkinson, primary)
    if any(not value.is_finite() for value in values):
        return None
    return {
        "target_version": target_version,
        "primary": _format(primary),
        "trailing_volatility_20": _format(scale),
        "next_abs_log_return": _format(next_abs),
        "next_high_low_log_range": _format(next_range),
        "next_parkinson_volatility": _format(parkinson),
        "next_abs_log_return_minus_trailing_volatility_20": _format(next_abs - scale),
    }


def _build_report(
    *,
    protocol: FinalStudyProtocolConfig,
    dataset: dict[str, object],
    rows: list[dict[str, object]],
    candidate_count: int,
    candidate_by_ticker: Counter[str],
    excluded: Counter[str],
    excluded_by_ticker: Counter[tuple[str, str]],
    exclusion_date_bounds: dict[str, tuple[date, date]],
    systematic_missing_sessions: list[dict[str, object]],
) -> dict[str, object]:
    ticker_counts = Counter(str(row["ticker"]) for row in rows)
    ticker_coverage = {}
    for ticker in sorted(candidate_by_ticker):
        reasons = {
            reason: count
            for (reason_ticker, reason), count in sorted(excluded_by_ticker.items())
            if reason_ticker == ticker
        }
        ticker_coverage[ticker] = {
            "candidate_row_count": candidate_by_ticker[ticker],
            "eligible_row_count": ticker_counts[ticker],
            "excluded_row_count": sum(reasons.values()),
            "excluded_row_counts": reasons,
        }
    outer_counts = []
    for fold in protocol.outer_evaluation.folds:
        training = [
            row
            for row in rows
            if fold.train_start <= date.fromisoformat(str(row["feature_session"])) <= fold.train_end
            and date.fromisoformat(str(row["target_session"])) < fold.evaluation_start
        ]
        evaluation = [
            row
            for row in rows
            if fold.evaluation_start
            <= date.fromisoformat(str(row["feature_session"]))
            <= fold.evaluation_end
        ]
        outer_counts.append(
            {
                "name": fold.name,
                "training_row_count": len(training),
                "evaluation_row_count": len(evaluation),
                "evaluation_ticker_counts": dict(
                    sorted(Counter(str(row["ticker"]) for row in evaluation).items())
                ),
            }
        )
    excluded_count = sum(excluded.values())
    if candidate_count != len(rows) + excluded_count:
        raise ValueError("candidate accounting does not reconcile")
    return {
        "report_version": REPORT_VERSION,
        "passed": bool(rows),
        "dataset_version": DATASET_VERSION,
        "dataset_sha256": dataset["sha256"],
        "market_dataset_sha256": dataset["market_dataset_sha256"],
        "f1_protocol_config_sha256": dataset["f1_protocol_config_sha256"],
        "feature_config_sha256": dataset["feature_config_sha256"],
        "target_version": dataset["target_version"],
        "candidate_row_count": candidate_count,
        "eligible_row_count": len(rows),
        "excluded_row_count": excluded_count,
        "excluded_row_counts": dict(sorted(excluded.items())),
        "exclusion_feature_date_ranges": {
            reason: {"start": bounds[0].isoformat(), "end": bounds[1].isoformat()}
            for reason, bounds in sorted(exclusion_date_bounds.items())
        },
        "ticker_row_counts": dict(sorted(ticker_counts.items())),
        "ticker_coverage": ticker_coverage,
        "systematic_missing_stock_sessions": systematic_missing_sessions,
        "data_quality_warnings": (
            [
                "Benchmark sessions missing stock bars for at least two tickers were excluded "
                "under the frozen consecutive-session contract."
            ]
            if systematic_missing_sessions
            else []
        ),
        "feature_date_start": rows[0]["feature_session"] if rows else None,
        "feature_date_end": rows[-1]["feature_session"] if rows else None,
        "target_date_start": min(str(row["target_session"]) for row in rows) if rows else None,
        "target_date_end": max(str(row["target_session"]) for row in rows) if rows else None,
        "outer_fold_counts": outer_counts,
        "duplicate_identity_count": 0,
        "feature_count": len(FEATURE_NAMES),
        "preprocessing_fitted": False,
        "models_trained": False,
        "binary_labels_materialized": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }


def _record_exclusion(
    excluded: Counter[str],
    excluded_by_ticker: Counter[tuple[str, str]],
    date_bounds: dict[str, tuple[date, date]],
    reason: str,
    ticker: str,
    feature_session: date,
) -> None:
    excluded[reason] += 1
    excluded_by_ticker[(ticker, reason)] += 1
    bounds = date_bounds.get(reason)
    date_bounds[reason] = (
        min(bounds[0], feature_session) if bounds else feature_session,
        max(bounds[1], feature_session) if bounds else feature_session,
    )


def _systematic_missing_stock_sessions(
    benchmark_sessions: list[date],
    stock_bars: dict[str, dict[date, dict[str, object]]],
    study_start: date,
    study_end: date,
) -> list[dict[str, object]]:
    output = []
    for session in benchmark_sessions:
        if not study_start <= session <= study_end:
            continue
        missing = sorted(
            ticker for ticker, bars in stock_bars.items() if session not in bars
        )
        if len(missing) >= 2:
            output.append(
                {
                    "benchmark_session": session.isoformat(),
                    "missing_ticker_count": len(missing),
                    "missing_tickers": missing,
                }
            )
    return output


def _verify_contracts(
    protocol: FinalStudyProtocolConfig,
    feature_config: RiskFeatureConfig,
    market_config: RiskMarketDatasetConfig,
) -> None:
    if tuple(protocol.features.fixed_feature_names) != FEATURE_NAMES:
        raise ValueError("F1 feature names differ from risk-features-v1")
    if tuple(feature_config.feature_names) != FEATURE_NAMES:
        raise ValueError("feature config differs from risk-features-v1")
    if feature_config.market_timezone != market_config.market_timezone:
        raise ValueError("feature and market timezones differ")
    if feature_config.required_consecutive_sessions < 35:
        raise ValueError("final study requires the frozen 35-session feature history")


def _verify_market_dataset(
    protocol: FinalStudyProtocolConfig, market_dataset: dict[str, object]
) -> None:
    if market_dataset.get("schema_version") != "risk-market-dataset-v1":
        raise ValueError("unexpected market dataset schema")
    expected = market_dataset.get("sha256")
    content = {key: value for key, value in market_dataset.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError("market dataset SHA-256 mismatch")
    if expected != protocol.historical_market_dataset.sha256:
        raise ValueError("market dataset differs from frozen F1 lineage")
    if market_dataset.get("models_trained") is not False:
        raise ValueError("market dataset model-training flag is invalid")


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


def _verify_unique_rows(rows: list[dict[str, object]]) -> None:
    identities = [(str(row["ticker"]), str(row["feature_session"])) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate ticker/feature-session identity")
    for row in rows:
        content = {key: value for key, value in row.items() if key != "row_sha256"}
        if row.get("row_sha256") != _hash(content):
            raise ValueError("row SHA-256 mismatch")


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
