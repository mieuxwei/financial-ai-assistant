from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pipelines.features.final_study_builder import (
    _benchmark_market,
    _calculate_target,
    _hash,
    _population_std,
    _stock_market,
    _verify_market_dataset,
)
from pipelines.features.risk_builder import FEATURE_NAMES, RiskFeatureConfig
from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    canonical_config_sha256,
)
from research.risk_labels.protocol import linear_quantile

AUDIT_VERSION = "final-study-target-feature-coverage-audit-v1"
UNKNOWN_REGIME = "UNAVAILABLE_DUE_TO_COVERAGE_GAP"
REGIMES = ("LOW", "MIDDLE", "HIGH")

FEATURE_AVAILABILITY = {
    "return_log_1": "post_close_t",
    "return_log_5": "post_close_t_trailing",
    "return_log_10": "post_close_t_trailing",
    "return_log_20": "post_close_t_trailing",
    "overnight_gap_log_1": "post_close_t",
    "close_ma_deviation_5": "post_close_t_trailing",
    "close_ma_deviation_20": "post_close_t_trailing",
    "volume_log_change_1p_1": "post_close_t",
    "volume_zscore_20": "post_close_t_trailing",
    "zero_volume_flag": "post_close_t",
    "volatility_log_return_5": "post_close_t_trailing",
    "volatility_log_return_20": "post_close_t_trailing",
    "high_low_log_range_1": "post_close_t",
    "atr_14_normalized": "post_close_t_trailing",
    "parkinson_mean_5": "post_close_t_trailing",
    "rsi_14": "post_close_t_trailing",
    "macd_12_26_normalized": "post_close_t_trailing",
    "macd_signal_9_normalized": "post_close_t_trailing",
    "benchmark_return_log_1": "same_benchmark_session_post_close_t",
    "benchmark_return_log_20": "same_benchmark_session_post_close_t_trailing",
    "benchmark_volatility_log_return_20": "same_benchmark_session_post_close_t_trailing",
    "stock_minus_benchmark_return_log_1": "same_benchmark_session_post_close_t",
    "benchmark_drawdown_20": "same_benchmark_session_post_close_t_trailing",
}


class CoverageBiasAuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["final-study-coverage-bias-audit-config-v1"]
    audit_version: Literal["final-study-target-feature-coverage-audit-v1"]
    dataset_version: Literal["final-volatility-surprise-dataset-v1"]
    axes: tuple[Literal["ticker", "calendar_year", "outer_fold", "volatility_regime"], ...]
    minimum_group_candidate_rows: int = Field(ge=1)
    abnormal_absolute_excess_rate: float = Field(gt=0, lt=1)
    abnormal_rate_ratio: float = Field(gt=1)
    unavailable_regime_warning_rate: float = Field(gt=0, lt=1)
    volatility_regime_quantiles: tuple[float, float]
    volatility_regime_cutoff_fit: Literal["outer_training_rows_only"]
    unknown_regime_label: Literal["UNAVAILABLE_DUE_TO_COVERAGE_GAP"]
    downgraded_conclusion: Literal[
        "DOCUMENTED_DATA_LIMITATION_NOT_DETECTED_AS_COVERAGE_BIAS"
    ]
    concentrated_conclusion: Literal[
        "DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION"
    ]
    no_missing_at_random_claim: Literal[True]

    @field_validator("axes")
    @classmethod
    def exact_axes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = ("ticker", "calendar_year", "outer_fold", "volatility_regime")
        if value != expected:
            raise ValueError("coverage audit axes drifted")
        return value

    @field_validator("volatility_regime_quantiles")
    @classmethod
    def ordered_quantiles(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not 0 < value[0] < value[1] < 1:
            raise ValueError("volatility regime quantiles must be ordered inside (0, 1)")
        return value


def load_coverage_audit_config(path: Path) -> CoverageBiasAuditConfig:
    return CoverageBiasAuditConfig.model_validate_json(path.read_text(encoding="utf-8"))


def audit_final_study_dataset(
    config: CoverageBiasAuditConfig,
    protocol: FinalStudyProtocolConfig,
    feature_config: RiskFeatureConfig,
    market_dataset: dict[str, object],
    dataset: dict[str, object],
) -> dict[str, object]:
    _verify_market_dataset(protocol, market_dataset)
    _verify_dataset_hash(dataset)
    if dataset.get("schema_version") != config.dataset_version:
        raise ValueError("unexpected final-study dataset version")
    if dataset.get("market_dataset_sha256") != market_dataset.get("sha256"):
        raise ValueError("final-study/market lineage mismatch")
    if dataset.get("f1_protocol_config_sha256") != canonical_config_sha256(protocol):
        raise ValueError("final-study/F1 protocol lineage mismatch")
    expected_feature_sha = _hash(feature_config.model_dump(mode="json"))
    if dataset.get("feature_config_sha256") != expected_feature_sha:
        raise ValueError("final-study feature-config lineage mismatch")

    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    benchmark_sessions, _ = _benchmark_market(market_dataset)
    stock_bars = _stock_market(market_dataset, market_config)
    rows = dataset.get("rows")
    if not isinstance(rows, list):
        raise TypeError("final-study rows must be a list")
    row_audit = _audit_rows(
        protocol,
        feature_config,
        benchmark_sessions,
        stock_bars,
        rows,
    )
    coverage = _coverage_bias_audit(
        config,
        protocol,
        benchmark_sessions,
        stock_bars,
        rows,
    )
    return {
        "report_version": AUDIT_VERSION,
        "passed": row_audit["passed"],
        "dataset_sha256": dataset["sha256"],
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "feature_config_sha256": expected_feature_sha,
        "row_contract_audit": row_audit,
        "feature_availability": FEATURE_AVAILABILITY,
        "coverage_bias_audit": coverage,
        "models_trained": False,
        "preprocessing_fitted": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }


def assess_concentration(
    config: CoverageBiasAuditConfig,
    axis: str,
    groups: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    candidates = sum(int(group["candidate_row_count"]) for group in groups.values())
    exclusions = sum(int(group["excluded_row_count"]) for group in groups.values())
    baseline = exclusions / candidates if candidates else 0.0
    findings = []
    for name, group in sorted(groups.items()):
        count = int(group["candidate_row_count"])
        rate = float(group["exclusion_rate"])
        ratio = rate / baseline if baseline > 0 else math.inf if rate > 0 else 1.0
        if (
            count >= config.minimum_group_candidate_rows
            and rate - baseline > config.abnormal_absolute_excess_rate
            and ratio > config.abnormal_rate_ratio
        ):
            findings.append(
                {
                    "axis": axis,
                    "group": name,
                    "candidate_row_count": count,
                    "exclusion_rate": round(rate, 10),
                    "axis_baseline_exclusion_rate": round(baseline, 10),
                    "rate_ratio": round(ratio, 10),
                }
            )
    return findings


def _audit_rows(
    protocol: FinalStudyProtocolConfig,
    feature_config: RiskFeatureConfig,
    benchmark_sessions: list[date],
    stock_bars: dict[str, dict[date, dict[str, object]]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    benchmark_index = {session: index for index, session in enumerate(benchmark_sessions)}
    seen: set[tuple[str, str]] = set()
    previous_identity: tuple[str, str] | None = None
    for row in rows:
        ticker = str(row["ticker"])
        feature_value = str(row["feature_session"])
        identity = (feature_value, ticker)
        if previous_identity is not None and identity <= previous_identity:
            raise ValueError("final-study rows are not uniquely ordered")
        previous_identity = identity
        unique_identity = (ticker, feature_value)
        if unique_identity in seen:
            raise ValueError("duplicate ticker/feature-session identity")
        seen.add(unique_identity)
        feature_session = date.fromisoformat(feature_value)
        target_session = date.fromisoformat(str(row["target_session"]))
        index = benchmark_index.get(feature_session)
        if index is None or index + 1 >= len(benchmark_sessions):
            raise ValueError("feature session lacks exact next benchmark session")
        if target_session != benchmark_sessions[index + 1]:
            raise ValueError("target is not the exact next benchmark session")
        cutoff = datetime.fromisoformat(str(row["information_cutoff"]))
        if cutoff.tzinfo is None or cutoff.date() != feature_session:
            raise ValueError("information cutoff is not timezone-aware on t")
        features = row.get("features")
        if not isinstance(features, dict) or set(features) != set(FEATURE_NAMES):
            raise ValueError("row features differ from the frozen feature contract")
        if set(features) & set(protocol.features.forbidden_feature_names):
            raise ValueError("target/future field entered feature mapping")
        if any(not math.isfinite(float(value)) for value in features.values()):
            raise ValueError("non-finite feature value")
        feature_payload = {
            "ticker": ticker,
            "feature_session": feature_value,
            "information_cutoff": row["information_cutoff"],
            "features": features,
        }
        if row.get("feature_values_sha256") != _hash(feature_payload):
            raise ValueError("feature-values SHA-256 mismatch")
        start = index - protocol.primary_target.trailing_sessions
        if start < 0:
            raise ValueError("target row lacks frozen trailing history")
        history_sessions = benchmark_sessions[start : index + 1]
        ticker_bars = stock_bars[ticker]
        if any(session not in ticker_bars for session in (*history_sessions, target_session)):
            raise ValueError("eligible row lacks market bars required to reproduce target")
        expected_target = _calculate_target(
            [ticker_bars[session] for session in history_sessions],
            ticker_bars[target_session],
            protocol.primary_target.name,
            Decimal(str(protocol.primary_target.minimum_denominator_exclusive)),
        )
        _audit_target(protocol, row["target"], expected_target)
        row_content = {key: value for key, value in row.items() if key != "row_sha256"}
        if row.get("row_sha256") != _hash(row_content):
            raise ValueError("row SHA-256 mismatch")
    return {
        "passed": True,
        "row_count": len(rows),
        "unique_identity_count": len(seen),
        "feature_count": len(FEATURE_NAMES),
        "exact_next_session_violation_count": 0,
        "target_feature_overlap_count": 0,
        "non_finite_feature_count": 0,
        "non_finite_target_count": 0,
        "row_hash_mismatch_count": 0,
    }


def _audit_target(
    protocol: FinalStudyProtocolConfig,
    raw: object,
    expected: dict[str, object] | None,
) -> None:
    if not isinstance(raw, dict):
        raise TypeError("target must be an object")
    if raw.get("target_version") != protocol.primary_target.name:
        raise ValueError("target version mismatch")
    scale = Decimal(str(raw["trailing_volatility_20"]))
    next_abs = Decimal(str(raw["next_abs_log_return"]))
    primary = Decimal(str(raw["primary"]))
    additive = Decimal(str(raw["next_abs_log_return_minus_trailing_volatility_20"]))
    values = (scale, next_abs, primary, additive)
    if any(not value.is_finite() for value in values):
        raise ValueError("non-finite target value")
    if scale <= Decimal(str(protocol.primary_target.minimum_denominator_exclusive)):
        raise ValueError("target denominator violates frozen near-zero policy")
    if expected is None or raw != expected:
        raise ValueError("target payload does not reproduce from frozen market bars")


def _coverage_bias_audit(
    config: CoverageBiasAuditConfig,
    protocol: FinalStudyProtocolConfig,
    benchmark_sessions: list[date],
    stock_bars: dict[str, dict[date, dict[str, object]]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    eligible = {(str(row["ticker"]), str(row["feature_session"])) for row in rows}
    study_start = min(fold.train_start for fold in protocol.outer_evaluation.folds)
    study_end = max(fold.evaluation_end for fold in protocol.outer_evaluation.folds)
    candidate_sessions = [s for s in benchmark_sessions if study_start <= s <= study_end]
    counters: dict[str, Counter[tuple[str, str]]] = {
        "ticker": Counter(),
        "calendar_year": Counter(),
        "outer_fold": Counter(),
    }
    for ticker in sorted(stock_bars):
        for session in candidate_sessions:
            excluded = (ticker, session.isoformat()) not in eligible
            _increment(counters["ticker"], ticker, excluded)
            _increment(counters["calendar_year"], str(session.year), excluded)
            fold_name = _evaluation_fold_name(protocol, session)
            if fold_name is not None:
                _increment(counters["outer_fold"], fold_name, excluded)

    tables = {axis: _group_table(counter) for axis, counter in counters.items()}
    regime_table, nested_regimes = _regime_coverage(
        protocol,
        benchmark_sessions,
        stock_bars,
        rows,
        eligible,
    )
    known_regime_table = {
        key: value for key, value in regime_table.items() if key != UNKNOWN_REGIME
    }
    tables["volatility_regime"] = regime_table
    findings = []
    for axis in ("ticker", "calendar_year", "outer_fold"):
        findings.extend(assess_concentration(config, axis, tables[axis]))
    findings.extend(
        assess_concentration(config, "volatility_regime", known_regime_table)
    )
    unavailable = regime_table.get(
        UNKNOWN_REGIME,
        {"candidate_row_count": 0, "excluded_row_count": 0, "exclusion_rate": 0.0},
    )
    regime_candidates = sum(
        int(group["candidate_row_count"]) for group in regime_table.values()
    )
    unavailable_rate = (
        int(unavailable["candidate_row_count"]) / regime_candidates if regime_candidates else 0.0
    )
    downgrade_allowed = (
        not findings and unavailable_rate <= config.unavailable_regime_warning_rate
    )
    return {
        "decision_rule": {
            "minimum_group_candidate_rows": config.minimum_group_candidate_rows,
            "abnormal_absolute_excess_rate": config.abnormal_absolute_excess_rate,
            "abnormal_rate_ratio": config.abnormal_rate_ratio,
            "both_thresholds_required": True,
            "volatility_regime_cutoffs": "outer-training-only tertiles",
        },
        "group_tables": tables,
        "outer_fold_volatility_regimes": nested_regimes,
        "abnormal_concentration_findings": findings,
        "unavailable_regime_candidate_rate": round(unavailable_rate, 10),
        "coverage_warning_downgrade_allowed": downgrade_allowed,
        "conclusion": (
            config.downgraded_conclusion
            if downgrade_allowed
            else config.concentrated_conclusion
        ),
        "missing_at_random_claimed": False,
    }


def _regime_coverage(
    protocol: FinalStudyProtocolConfig,
    benchmark_sessions: list[date],
    stock_bars: dict[str, dict[date, dict[str, object]]],
    rows: list[dict[str, object]],
    eligible: set[tuple[str, str]],
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    benchmark_index = {session: index for index, session in enumerate(benchmark_sessions)}
    total: Counter[tuple[str, str]] = Counter()
    nested: dict[str, object] = {}
    for fold in protocol.outer_evaluation.folds:
        training_scales = [
            Decimal(str(row["target"]["trailing_volatility_20"]))
            for row in rows
            if fold.train_start
            <= date.fromisoformat(str(row["feature_session"]))
            <= fold.train_end
            and date.fromisoformat(str(row["target_session"])) < fold.evaluation_start
        ]
        low_cutoff = linear_quantile(training_scales, Decimal("0.333333333333"))
        high_cutoff = linear_quantile(training_scales, Decimal("0.666666666667"))
        fold_counter: Counter[tuple[str, str]] = Counter()
        for ticker, bars in sorted(stock_bars.items()):
            for session in benchmark_sessions:
                if not fold.evaluation_start <= session <= fold.evaluation_end:
                    continue
                scale = _trailing_scale(session, benchmark_sessions, benchmark_index, bars)
                regime = _regime(scale, low_cutoff, high_cutoff)
                excluded = (ticker, session.isoformat()) not in eligible
                _increment(total, regime, excluded)
                _increment(fold_counter, regime, excluded)
        nested[fold.name] = {
            "training_row_count_for_cutoffs": len(training_scales),
            "low_middle_cutoff": str(low_cutoff),
            "middle_high_cutoff": str(high_cutoff),
            "groups": _group_table(fold_counter),
        }
    return _group_table(total), nested


def _trailing_scale(
    session: date,
    benchmark_sessions: list[date],
    benchmark_index: dict[date, int],
    bars: dict[date, dict[str, object]],
) -> Decimal | None:
    index = benchmark_index[session]
    start = index - 20
    if start < 0:
        return None
    sessions = benchmark_sessions[start : index + 1]
    if any(item not in bars for item in sessions):
        return None
    adjusted = [Decimal(str(bars[item]["adjusted_close"])) for item in sessions]
    returns = []
    for current, previous in zip(adjusted[1:], adjusted[:-1], strict=True):
        if current <= 0 or previous <= 0:
            return None
        returns.append((current / previous).ln())
    scale = _population_std(returns)
    return scale if scale.is_finite() else None


def _regime(scale: Decimal | None, low: Decimal, high: Decimal) -> str:
    if scale is None:
        return UNKNOWN_REGIME
    if scale <= low:
        return "LOW"
    if scale <= high:
        return "MIDDLE"
    return "HIGH"


def _evaluation_fold_name(protocol: FinalStudyProtocolConfig, session: date) -> str | None:
    for fold in protocol.outer_evaluation.folds:
        if fold.evaluation_start <= session <= fold.evaluation_end:
            return fold.name
    return None


def _increment(counter: Counter[tuple[str, str]], group: str, excluded: bool) -> None:
    counter[(group, "candidate")] += 1
    if excluded:
        counter[(group, "excluded")] += 1


def _group_table(counter: Counter[tuple[str, str]]) -> dict[str, dict[str, object]]:
    groups = sorted({group for group, _ in counter})
    return {
        group: {
            "candidate_row_count": counter[(group, "candidate")],
            "excluded_row_count": counter[(group, "excluded")],
            "eligible_row_count": counter[(group, "candidate")]
            - counter[(group, "excluded")],
            "exclusion_rate": round(
                counter[(group, "excluded")] / counter[(group, "candidate")], 10
            ),
        }
        for group in groups
    }


def _verify_dataset_hash(dataset: dict[str, object]) -> None:
    expected = dataset.get("sha256")
    content = {key: value for key, value in dataset.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError("final-study dataset SHA-256 mismatch")


def canonical_audit_config_sha256(config: CoverageBiasAuditConfig) -> str:
    payload = config.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
