from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median

import numpy as np

from research.evaluation.post_m8_research_boundaries import (
    HISTORICAL_M7_THRESHOLD,
    M7_EVALUATION_SHA256,
    M7_PREDICTION_COUNT,
    M8_ANALYSIS_SHA256,
)

ANALYSIS_VERSION = "post-m8-conditional-risk-analysis-v1"
REPORT_VERSION = "m9-conditional-risk-report-v1"
RAW_OUTCOMES = (
    "next_abs_log_return",
    "next_high_low_log_range",
    "next_parkinson_volatility",
)
OUTCOMES = (*RAW_OUTCOMES, "continuous_risk_outcome", "additive_volatility_surprise")
MINIMUM_GROUP_ROWS = 30


def load_config(path: Path) -> dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    historical = config["historical_evidence"]
    if config["schema_version"] != "post-m8-conditional-risk-config-v1":
        raise ValueError("unexpected M9 config schema")
    if config["status"] != "PROTOCOL_FROZEN_NOT_EXECUTED":
        raise ValueError("M9 protocol status drifted")
    if historical["m7_sealed_evaluation_sha256"] != M7_EVALUATION_SHA256:
        raise ValueError("M9 M7 hash binding drifted")
    if historical["m8_analysis_sha256"] != M8_ANALYSIS_SHA256:
        raise ValueError("M9 M8 hash binding drifted")
    if historical["m7_prediction_count"] != M7_PREDICTION_COUNT:
        raise ValueError("M9 expected prediction count drifted")
    if historical["historical_decision_threshold"] != HISTORICAL_M7_THRESHOLD:
        raise ValueError("M9 historical threshold drifted")
    if not config["analysis_only"] or any(
        config[field]
        for field in (
            "model_refit_allowed",
            "prediction_mutation_allowed",
            "threshold_change_allowed",
            "classifier_feedback_allowed",
        )
    ):
        raise ValueError("M9 is not analysis-only")
    return config


def verify_m9_inputs(
    config: dict[str, object],
    evaluation: dict[str, object],
    m8_analysis: dict[str, object],
) -> None:
    _verify_hash(evaluation, "M7 evaluation")
    _verify_hash(m8_analysis, "M8 analysis")
    historical = config["historical_evidence"]
    if evaluation["sha256"] != historical["m7_sealed_evaluation_sha256"]:
        raise ValueError("M7 evaluation does not match frozen M9 config")
    if m8_analysis["sha256"] != historical["m8_analysis_sha256"]:
        raise ValueError("M8 analysis does not match frozen M9 config")
    if m8_analysis["sealed_evaluation_sha256"] != evaluation["sha256"]:
        raise ValueError("M8/M7 lineage mismatch")
    if evaluation.get("evaluation_sequence") != 1:
        raise ValueError("M7 evaluation sequence is not one")
    if len(evaluation.get("rows", [])) != historical["m7_prediction_count"]:
        raise ValueError("M7 prediction count changed")
    if m8_analysis.get("m7_rerun_performed") is not False:
        raise ValueError("M8 records an M7 rerun")
    if m8_analysis.get("model_or_threshold_selection_performed") is not False:
        raise ValueError("M8 records forbidden selection")


def analyze_conditional_risk(
    config: dict[str, object],
    evaluation: dict[str, object],
    m8_analysis: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    verify_m9_inputs(config, evaluation, m8_analysis)
    rows = _enriched_rows(evaluation, m8_analysis)
    aggregate = _comparison(rows)
    by_regime = _stratified_comparisons(rows, "stock_volatility_regime")
    by_ticker = _stratified_comparisons(rows, "ticker")
    by_quarter = _stratified_comparisons(rows, "calendar_quarter")
    composition = {
        axis: _composition(rows, axis)
        for axis in ("stock_volatility_regime", "ticker", "calendar_quarter")
    }
    standardization = {
        outcome: _regime_standardization(rows, outcome) for outcome in OUTCOMES
    }
    regressions = {outcome: _conditional_regression(rows, outcome) for outcome in OUTCOMES}
    direction_counts = {
        outcome: _ticker_direction_counts(by_ticker, outcome) for outcome in OUTCOMES
    }
    simpson = {
        outcome: _simpson_assessment(
            aggregate, by_regime, standardization[outcome], outcome
        )
        for outcome in OUTCOMES
    }
    conclusion = _conclusion(simpson)
    config_sha256 = _hash(config)
    content = {
        "schema_version": ANALYSIS_VERSION,
        "protocol_version": config["protocol_version"],
        "config_sha256": config_sha256,
        "m7_evaluation_sha256": evaluation["sha256"],
        "m8_analysis_sha256": m8_analysis["sha256"],
        "m7_prediction_count": len(rows),
        "historical_threshold": HISTORICAL_M7_THRESHOLD,
        "aggregate_comparison": aggregate,
        "stock_volatility_regime_comparison": by_regime,
        "ticker_comparison": by_ticker,
        "quarter_comparison": by_quarter,
        "ticker_direction_counts": direction_counts,
        "composition": composition,
        "regime_standardization": standardization,
        "conditional_regression_ols_hc3": regressions,
        "simpson_type_assessment": simpson,
        "conclusion": conclusion,
        "analysis_only": True,
        "m7_rerun_performed": False,
        "m8_rerun_performed": False,
        "model_refit_performed": False,
        "prediction_mutation_performed": False,
        "threshold_change_performed": False,
        "classifier_feedback_performed": False,
        "rows_persisted": False,
    }
    analysis = {**content, "sha256": _hash(content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "analysis_sha256": analysis["sha256"],
        **{key: value for key, value in content.items() if key != "rows_persisted"},
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return analysis, report


def _enriched_rows(
    evaluation: dict[str, object], m8_analysis: dict[str, object]
) -> list[dict[str, object]]:
    thresholds = m8_analysis["regime_thresholds"]["stock_volatility"]
    output = []
    identities = set()
    for row in evaluation["rows"]:
        identity = (str(row["ticker"]), str(row["feature_session"]))
        if identity in identities:
            raise ValueError("duplicate M7 prediction identity")
        identities.add(identity)
        probability = float(row["calibrated_probability"])
        predicted = probability >= HISTORICAL_M7_THRESHOLD
        expected = "HIGH_RISK" if predicted else "NORMAL"
        if row["predicted_label"] != expected:
            raise ValueError("stored M7 label differs from historical threshold")
        session = date.fromisoformat(str(row["feature_session"]))
        prior_volatility = float(row["features"]["volatility_log_return_20"])
        target = row["target"]
        enriched = {
            "ticker": str(row["ticker"]),
            "feature_session": session.isoformat(),
            "calendar_quarter": f"{session.year}-Q{(session.month - 1) // 3 + 1}",
            "predicted_high_risk": int(predicted),
            "stock_volatility_regime": _regime(prior_volatility, thresholds),
            "prior_stock_volatility": prior_volatility,
            "next_abs_log_return": float(target["next_abs_log_return"]),
            "next_high_low_log_range": float(target["next_high_low_log_range"]),
            "next_parkinson_volatility": float(target["next_parkinson_volatility"]),
            "continuous_risk_outcome": float(target["continuous_risk_outcome"]),
        }
        enriched["additive_volatility_surprise"] = (
            enriched["next_abs_log_return"] - prior_volatility
        )
        output.append(enriched)
    if len(output) != M7_PREDICTION_COUNT:
        raise ValueError("M9 row count differs from frozen M7 count")
    return sorted(output, key=lambda row: (row["feature_session"], row["ticker"]))


def _regime(value: float, thresholds: dict[str, object]) -> str:
    if value <= float(thresholds["low_upper"]):
        return "LOW"
    if value <= float(thresholds["middle_upper"]):
        return "MIDDLE"
    return "HIGH"


def _comparison(rows: list[dict[str, object]]) -> dict[str, object]:
    groups = {
        "NORMAL": [row for row in rows if not row["predicted_high_risk"]],
        "HIGH_RISK": [row for row in rows if row["predicted_high_risk"]],
    }
    summaries = {name: _outcome_summary(group) for name, group in groups.items()}
    differences = {
        outcome: summaries["HIGH_RISK"][outcome]["mean"]
        - summaries["NORMAL"][outcome]["mean"]
        for outcome in OUTCOMES
    }
    return {**summaries, "high_minus_normal_mean": differences}


def _outcome_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {"row_count": len(rows)}
    for outcome in OUTCOMES:
        values = [float(row[outcome]) for row in rows]
        output[outcome] = {
            "mean": float(np.mean(values)),
            "median": float(median(values)),
        }
    return output


def _stratified_comparisons(
    rows: list[dict[str, object]], key: str
) -> dict[str, object]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    output = {}
    for name, group in sorted(groups.items()):
        predicted_counts = Counter(
            "HIGH_RISK" if row["predicted_high_risk"] else "NORMAL" for row in group
        )
        smallest_group = min(
            predicted_counts.get("HIGH_RISK", 0), predicted_counts.get("NORMAL", 0)
        )
        if smallest_group < MINIMUM_GROUP_ROWS:
            output[name] = {
                "status": "INSUFFICIENT_PREDICTED_GROUP_ROWS",
                "row_count": len(group),
                "predicted_group_counts": dict(sorted(predicted_counts.items())),
                "comparison": None,
            }
        else:
            output[name] = {
                "status": "OK",
                "row_count": len(group),
                "predicted_group_counts": dict(sorted(predicted_counts.items())),
                "comparison": _comparison(group),
            }
    return output


def _composition(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    categories = sorted({str(row[key]) for row in rows})
    groups = {
        "NORMAL": [row for row in rows if not row["predicted_high_risk"]],
        "HIGH_RISK": [row for row in rows if row["predicted_high_risk"]],
    }
    proportions = {}
    for group_name, group in groups.items():
        counts = Counter(str(row[key]) for row in group)
        proportions[group_name] = {
            category: {
                "row_count": counts.get(category, 0),
                "proportion": counts.get(category, 0) / len(group),
            }
            for category in categories
        }
    differences = {
        category: proportions["HIGH_RISK"][category]["proportion"]
        - proportions["NORMAL"][category]["proportion"]
        for category in categories
    }
    total_variation = 0.5 * sum(abs(value) for value in differences.values())
    return {
        "NORMAL": proportions["NORMAL"],
        "HIGH_RISK": proportions["HIGH_RISK"],
        "high_minus_normal_proportion": differences,
        "total_variation_distance": total_variation,
    }


def _regime_standardization(
    rows: list[dict[str, object]], outcome: str
) -> dict[str, object]:
    regimes = sorted({str(row["stock_volatility_regime"]) for row in rows})
    pooled_counts = Counter(str(row["stock_volatility_regime"]) for row in rows)
    weights = {regime: pooled_counts[regime] / len(rows) for regime in regimes}
    standardized = {}
    regime_differences = {}
    for predicted_name, predicted_value in (("NORMAL", 0), ("HIGH_RISK", 1)):
        group_means = {}
        for regime in regimes:
            values = [
                float(row[outcome])
                for row in rows
                if row["predicted_high_risk"] == predicted_value
                and row["stock_volatility_regime"] == regime
            ]
            if not values:
                raise ValueError("regime/prediction cell is empty")
            group_means[regime] = float(np.mean(values))
        standardized[predicted_name] = sum(
            weights[regime] * group_means[regime] for regime in regimes
        )
        standardized[f"{predicted_name}_regime_means"] = group_means
    for regime in regimes:
        regime_differences[regime] = (
            standardized["HIGH_RISK_regime_means"][regime]
            - standardized["NORMAL_regime_means"][regime]
        )
    observed = _comparison(rows)["high_minus_normal_mean"][outcome]
    conditional = standardized["HIGH_RISK"] - standardized["NORMAL"]
    return {
        "common_pooled_regime_weights": weights,
        "observed_aggregate_difference": observed,
        "standardized_high_risk_mean": standardized["HIGH_RISK"],
        "standardized_normal_mean": standardized["NORMAL"],
        "standardized_within_regime_difference": conditional,
        "composition_component": observed - conditional,
        "within_regime_differences": regime_differences,
    }


def _conditional_regression(
    rows: list[dict[str, object]], outcome: str
) -> dict[str, object]:
    tickers = sorted({str(row["ticker"]) for row in rows})
    quarters = sorted({str(row["calendar_quarter"]) for row in rows})
    columns = ["intercept", "predicted_high_risk", "prior_stock_volatility"]
    columns += [f"ticker[{value}]" for value in tickers[1:]]
    columns += [f"quarter[{value}]" for value in quarters[1:]]
    matrix = []
    values = []
    for row in rows:
        matrix.append(
            [1.0, float(row["predicted_high_risk"]), float(row["prior_stock_volatility"])]
            + [float(row["ticker"] == value) for value in tickers[1:]]
            + [float(row["calendar_quarter"] == value) for value in quarters[1:]]
        )
        values.append(float(row[outcome]))
    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    xtx_inverse = np.linalg.pinv(x.T @ x)
    beta = xtx_inverse @ x.T @ y
    residual = y - x @ beta
    leverage = np.einsum("ij,jk,ik->i", x, xtx_inverse, x)
    adjusted = residual / np.maximum(1.0 - leverage, 1e-12)
    meat = x.T @ ((adjusted**2)[:, None] * x)
    covariance = xtx_inverse @ meat @ xtx_inverse
    standard_error = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    index = columns.index("predicted_high_risk")
    coefficient = float(beta[index])
    se = float(standard_error[index])
    z_value = coefficient / se if se else math.inf
    p_value = math.erfc(abs(z_value) / math.sqrt(2)) if math.isfinite(z_value) else 0.0
    return {
        "estimator": "ols_hc3",
        "row_count": len(rows),
        "design_rank": int(np.linalg.matrix_rank(x)),
        "parameter_count": x.shape[1],
        "reference_ticker": tickers[0],
        "reference_quarter": quarters[0],
        "predicted_high_risk_coefficient": coefficient,
        "hc3_standard_error": se,
        "normal_approximation_z": z_value,
        "two_sided_normal_approximation_p": p_value,
        "confidence_interval_95": {
            "lower": coefficient - 1.959963984540054 * se,
            "upper": coefficient + 1.959963984540054 * se,
        },
        "used_for_classifier_selection_or_tuning": False,
        "causal_interpretation_allowed": False,
    }


def _ticker_direction_counts(
    comparisons: dict[str, object], outcome: str
) -> dict[str, object]:
    counts = Counter()
    tickers = {"positive": [], "negative": [], "zero": [], "insufficient": []}
    for ticker, result in comparisons.items():
        if result["status"] != "OK":
            counts["insufficient"] += 1
            tickers["insufficient"].append(ticker)
            continue
        difference = result["comparison"]["high_minus_normal_mean"][outcome]
        direction = "positive" if difference > 0 else "negative" if difference < 0 else "zero"
        counts[direction] += 1
        tickers[direction].append(ticker)
    return {"counts": dict(sorted(counts.items())), "tickers": tickers}


def _simpson_assessment(
    aggregate: dict[str, object],
    by_regime: dict[str, object],
    standardization: dict[str, object],
    outcome: str,
) -> dict[str, object]:
    aggregate_difference = aggregate["high_minus_normal_mean"][outcome]
    regime_differences = {
        regime: result["comparison"]["high_minus_normal_mean"][outcome]
        for regime, result in by_regime.items()
        if result["status"] == "OK"
    }
    all_within_positive = bool(regime_differences) and all(
        value > 0 for value in regime_differences.values()
    )
    all_within_negative = bool(regime_differences) and all(
        value < 0 for value in regime_differences.values()
    )
    reversal = (aggregate_difference < 0 and all_within_positive) or (
        aggregate_difference > 0 and all_within_negative
    )
    return {
        "aggregate_difference": aggregate_difference,
        "within_regime_differences": regime_differences,
        "all_within_regime_differences_positive": all_within_positive,
        "all_within_regime_differences_negative": all_within_negative,
        "aggregate_within_regime_direction_reversal": reversal,
        "standardized_within_regime_difference": standardization[
            "standardized_within_regime_difference"
        ],
        "composition_component": standardization["composition_component"],
        "classification": (
            "SIMPSON_TYPE_COMPOSITION_EFFECT_SUPPORTED_DESCRIPTIVELY"
            if reversal
            else "NO_COMPLETE_DIRECTION_REVERSAL"
        ),
        "causal_simpsons_paradox_claim_allowed": False,
    }


def _conclusion(simpson: dict[str, object]) -> dict[str, object]:
    raw_reversals = [
        outcome
        for outcome in RAW_OUTCOMES
        if simpson[outcome]["aggregate_within_regime_direction_reversal"]
    ]
    normalized = simpson["continuous_risk_outcome"]
    return {
        "raw_outcomes_with_simpson_type_reversal": raw_reversals,
        "all_three_raw_outcomes_reverse": set(raw_reversals) == set(RAW_OUTCOMES),
        "normalized_outcome_aggregate_difference": normalized["aggregate_difference"],
        "supported_framing": (
            "modest_heterogeneous_stock_normalized_volatility_surprise_discrimination"
        ),
        "absolute_volatility_predictor_claim_supported": False,
        "no_volatility_information_claim_supported": False,
        "definitive_causal_simpsons_paradox_claim_supported": False,
    }


def _verify_hash(payload: dict[str, object], name: str) -> None:
    expected = payload.get("sha256")
    content = {key: value for key, value in payload.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError(f"{name} SHA-256 mismatch")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


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
