from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from research.evaluation.operating_points import (
    _hash,
    _threshold_grid,
    _verify_hash,
    _verify_selection_row,
)
from research.modeling.metrics import uniform_calibration_bins
from research.modeling.temporal_validation import (
    RiskTemporalValidationConfig,
    _fold_rows,
    _verify_fold_rows,
)

ANALYSIS_VERSION = "post-m8-regime-threshold-analysis-v1"
REPORT_VERSION = "m11-regime-threshold-report-v1"
REGIMES = ("LOW", "MIDDLE", "HIGH")


def load_config(path: Path) -> dict[str, object]:
    config = __import__("json").loads(path.read_text(encoding="utf-8"))
    if config["schema_version"] != "post-m8-regime-threshold-config-v1":
        raise ValueError("unexpected M11 config schema")
    if config["status"] != "PROTOCOL_FROZEN_SEARCH_NOT_RUN":
        raise ValueError("M11 protocol status drifted")
    if config["model_policy"] != "ONE_FROZEN_MODEL_WITH_REGIME_AWARE_THRESHOLDS":
        raise ValueError("M11 model policy drifted")
    if config["separate_models_allowed"]:
        raise ValueError("M11 permits separate regime models")
    source = config["development_prediction_source"]
    if source["allowed_splits"] != ["train", "validation"]:
        raise ValueError("M11 source is not development-only")
    if source["latest_allowed_target_session"] != "2024-12-31":
        raise ValueError("M11 development cutoff drifted")
    if source["sealed_test_rows_allowed"] or source["m7_or_m8_labels_allowed"]:
        raise ValueError("M11 permits historical sealed evidence")
    regime = config["regime_definition"]
    if regime["development_cutoff_method"] != "expanding_training_history_tertiles_per_fold":
        raise ValueError("M11 regime cutoff method drifted")
    if regime["feature"] != "volatility_log_return_20":
        raise ValueError("M11 regime feature drifted")
    if regime["future_or_target_values_allowed"]:
        raise ValueError("M11 permits future regime information")
    if tuple(regime["labels"]) != REGIMES:
        raise ValueError("M11 regime labels drifted")
    return config


def assign_development_regimes(
    config: dict[str, object],
    temporal_config: RiskTemporalValidationConfig,
    feature_rows: list[dict[str, object]],
    development_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Assign each OOF row using cutoffs fitted only on its fold's earlier training history."""
    folds = {fold.name: fold for fold in temporal_config.folds[1:]}
    grouped = {name: [] for name in folds}
    for row in development_rows:
        _verify_selection_row(row, config)
        fold_name = str(row["fold"])
        if fold_name not in grouped:
            raise ValueError(f"unexpected M11 development fold: {fold_name}")
        grouped[fold_name].append(row)

    assigned: list[dict[str, object]] = []
    fold_evidence = []
    quantiles = config["regime_definition"]["quantiles"]
    for fold_name, fold in folds.items():
        train_rows, evaluation_rows = _fold_rows(feature_rows, fold)
        _verify_fold_rows(temporal_config, fold, train_rows, evaluation_rows)
        cutoffs = _tertile_cutoffs(train_rows, quantiles)
        expected = grouped[fold_name]
        if len(expected) != len(evaluation_rows):
            raise ValueError(f"{fold_name} OOF/evaluation row count mismatch")
        evaluation_keys = {
            (str(row["ticker"]), str(row["feature_session"])) for row in evaluation_rows
        }
        if {
            (str(row["ticker"]), str(row["feature_session"])) for row in expected
        } != evaluation_keys:
            raise ValueError(f"{fold_name} OOF/evaluation identity mismatch")
        for row in expected:
            assigned.append(
                {
                    **row,
                    "regime": _regime(float(row["volatility_log_return_20"]), cutoffs),
                }
            )
        fold_evidence.append(
            {
                "fold": fold_name,
                "cutoff_fit_train_end": fold.train_end.isoformat(),
                "evaluation_start": fold.evaluation_start.isoformat(),
                "training_row_count": len(train_rows),
                "evaluation_row_count": len(expected),
                "lower_tertile": cutoffs[0],
                "upper_tertile": cutoffs[1],
                "training_target_precedes_evaluation": max(
                    str(row["target"]["target_session"]) for row in train_rows
                ) < fold.evaluation_start.isoformat(),
            }
        )
    assigned.sort(key=lambda row: (row["feature_session"], row["ticker"]))

    cutoff_end = config["regime_definition"]["final_policy_cutoff_fit_period_end"]
    final_rows = [
        row
        for row in feature_rows
        if str(row["split"]) in config["development_prediction_source"]["allowed_splits"]
        and str(row["target"]["target_session"]) <= cutoff_end
    ]
    final_cutoffs = _tertile_cutoffs(final_rows, quantiles)
    evidence = {
        "method": "expanding_training_history_tertiles_per_fold",
        "boundary_rule": "LOW<=lower; MIDDLE<=upper; HIGH>upper",
        "folds": fold_evidence,
        "final_prospective_policy_cutoffs": {
            "fit_period_end": cutoff_end,
            "row_count": len(final_rows),
            "lower_tertile": final_cutoffs[0],
            "upper_tertile": final_cutoffs[1],
            "used_to_reassign_development_rows": False,
        },
    }
    return assigned, evidence


def analyze_regime_thresholds(
    config: dict[str, object],
    temporal_config: RiskTemporalValidationConfig,
    feature_dataset: dict[str, object],
    development_dataset: dict[str, object],
    m10_report: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    _verify_hash(feature_dataset, "M3 feature dataset")
    _verify_hash(development_dataset, "M10 development OOF dataset")
    _verify_inputs(config, feature_dataset, development_dataset, m10_report)
    feature_rows = feature_dataset["rows"]
    development_rows = development_dataset["rows"]
    assigned, cutoff_evidence = assign_development_regimes(
        config, temporal_config, feature_rows, development_rows
    )
    labels = np.asarray([row["high_risk_label"] for row in assigned], dtype=np.int8)
    probabilities = np.asarray(
        [row["calibrated_probability"] for row in assigned], dtype=np.float64
    )
    regimes = np.asarray([row["regime"] for row in assigned])
    regime_counts = {
        regime: {
            "row_count": int((regimes == regime).sum()),
            "positive_count": int(labels[regimes == regime].sum()),
        }
        for regime in REGIMES
    }
    grid = _threshold_grid(
        {**config["threshold_grid_per_regime"], "type": "inclusive_decimal_grid"}
    )
    tables = _regime_threshold_tables(labels, probabilities, regimes, grid)
    selected, eligible_count = select_regime_policy(tables, config["eligibility_constraints"])
    comparisons = {
        "historical_global_threshold_0.10": evaluate_policy(
            labels, probabilities, regimes, {regime: 0.10 for regime in REGIMES}
        )
    }
    for name in ("screening", "balanced", "precision"):
        mode = m10_report["operating_modes"][name]
        if mode["status"] != "DEVELOPMENT_POLICY_SELECTED_NOT_HOLDOUT_VALIDATED":
            raise ValueError(f"M10 {name} comparison policy is unavailable")
        threshold = float(mode["selected"]["threshold"])
        comparisons[f"m10_{name}_global_threshold_{threshold:.2f}"] = evaluate_policy(
            labels, probabilities, regimes, {regime: threshold for regime in REGIMES}
        )
    selected_policy = None
    status = "INCONCLUSIVE_NO_POLICY_SELECTED"
    if selected is not None:
        selected_policy = evaluate_policy(labels, probabilities, regimes, selected["thresholds"])
        selected_policy["selection_objective"] = selected["selection_objective"]
        status = "DEVELOPMENT_POLICY_SELECTED_NOT_HOLDOUT_VALIDATED"

    content = {
        "schema_version": ANALYSIS_VERSION,
        "protocol_version": config["protocol_version"],
        "config_sha256": _hash(config),
        "feature_dataset_sha256": feature_dataset["sha256"],
        "development_oof_dataset_sha256": development_dataset["sha256"],
        "m10_analysis_sha256": m10_report["analysis_sha256"],
        "development_row_count": len(assigned),
        "development_positive_count": int(labels.sum()),
        "development_period_end": max(row["target_session"] for row in assigned),
        "regime_counts": regime_counts,
        "regime_cutoff_evidence": cutoff_evidence,
        "threshold_grid_size_per_regime": len(grid),
        "threshold_triplet_candidate_count": len(grid) ** len(REGIMES),
        "eligible_candidate_count": eligible_count,
        "selection_status": status,
        "selected_regime_policy": selected_policy,
        "comparisons": comparisons,
        "calibration_table": uniform_calibration_bins(labels, probabilities, 10),
        "result_scope": "DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT",
        "one_frozen_model_used": True,
        "separate_regime_models_trained": False,
        "sealed_test_rows_used": 0,
        "m7_m8_m9_labels_or_outcomes_used": False,
        "m7_final_candidate_refit_performed": False,
        "m7_rerun_performed": False,
        "m8_rerun_performed": False,
        "m9_rerun_performed": False,
        "m10_oof_reconstructed_again": False,
        "raw_rows_persisted_in_analysis": False,
    }
    analysis = {**content, "sha256": _hash(content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "analysis_sha256": analysis["sha256"],
        **{key: value for key, value in content.items() if key != "schema_version"},
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return analysis, report


def select_regime_policy(
    tables: dict[str, dict[float, dict[str, object]]], constraints: dict[str, object]
) -> tuple[dict[str, object] | None, int]:
    for regime in REGIMES:
        sample = next(iter(tables[regime].values()))
        if sample["row_count"] < constraints["minimum_rows_per_regime"]:
            return None, 0
        if sample["positive_count"] < constraints["minimum_positive_rows_per_regime"]:
            return None, 0
    eligible_count = 0
    best = None
    best_score = None
    thresholds = tuple(tables[REGIMES[0]])
    for triplet in itertools.product(thresholds, repeat=3):
        items = [
            tables[regime][threshold]
            for regime, threshold in zip(REGIMES, triplet, strict=True)
        ]
        recall_values = [float(item["recall"]) for item in items]
        specificity_values = [float(item["specificity"]) for item in items]
        if min(recall_values) < constraints["minimum_each_regime_recall"]:
            continue
        if min(specificity_values) < constraints["minimum_each_regime_specificity"]:
            continue
        confusion = _sum_confusion(items)
        overall = _confusion_metrics(confusion)
        if overall["recall"] < constraints["minimum_overall_recall"]:
            continue
        if overall["specificity"] < constraints["minimum_overall_specificity"]:
            continue
        eligible_count += 1
        recall_range = max(recall_values) - min(recall_values)
        specificity_range = max(specificity_values) - min(specificity_values)
        primary = max(recall_range, specificity_range)
        alert_rates = [float(item["alert_rate"]) for item in items]
        alert_dispersion = max(alert_rates) - min(alert_rates)
        score = (-primary, overall["mcc"], overall["f1"], -alert_dispersion, *triplet)
        if best_score is None or score > best_score:
            best_score = score
            best = {
                "thresholds": dict(zip(REGIMES, triplet, strict=True)),
                "selection_objective": {
                    "max_recall_specificity_range": primary,
                    "recall_range": recall_range,
                    "specificity_range": specificity_range,
                    "overall_mcc": overall["mcc"],
                    "overall_f1": overall["f1"],
                    "alert_rate_dispersion": alert_dispersion,
                },
            }
    return best, eligible_count


def evaluate_policy(
    labels: np.ndarray,
    probabilities: np.ndarray,
    regimes: np.ndarray,
    thresholds: dict[str, float],
) -> dict[str, object]:
    predicted = np.zeros(len(labels), dtype=np.int8)
    per_regime = {}
    for regime in REGIMES:
        mask = regimes == regime
        predicted[mask] = (probabilities[mask] >= thresholds[regime]).astype(np.int8)
        confusion = _confusion(labels[mask], predicted[mask])
        metrics = _confusion_metrics(confusion)
        per_regime[regime] = {
            "threshold": thresholds[regime],
            "row_count": int(mask.sum()),
            "positive_count": int(labels[mask].sum()),
            **metrics,
            "confusion_matrix": confusion,
        }
    overall_confusion = _confusion(labels, predicted)
    overall = _confusion_metrics(overall_confusion)
    recall_values = [per_regime[regime]["recall"] for regime in REGIMES]
    specificity_values = [per_regime[regime]["specificity"] for regime in REGIMES]
    alert_values = [per_regime[regime]["alert_rate"] for regime in REGIMES]
    return {
        "thresholds": thresholds,
        "overall": {
            **overall,
            "pr_auc": float(average_precision_score(labels, probabilities)),
            "roc_auc": float(roc_auc_score(labels, probabilities)),
            "brier_score": float(brier_score_loss(labels, probabilities)),
            "confusion_matrix": overall_confusion,
        },
        "per_regime": per_regime,
        "recall_dispersion_range": max(recall_values) - min(recall_values),
        "specificity_dispersion_range": max(specificity_values) - min(specificity_values),
        "alert_rate_dispersion_range": max(alert_values) - min(alert_values),
    }


def _regime_threshold_tables(
    labels: np.ndarray, probabilities: np.ndarray, regimes: np.ndarray, grid: list[float]
) -> dict[str, dict[float, dict[str, object]]]:
    tables = {}
    for regime in REGIMES:
        mask = regimes == regime
        values = {}
        for threshold in grid:
            confusion = _confusion(labels[mask], (probabilities[mask] >= threshold).astype(np.int8))
            values[threshold] = {
                "row_count": int(mask.sum()),
                "positive_count": int(labels[mask].sum()),
                **_confusion_metrics(confusion),
                "confusion_matrix": confusion,
            }
        tables[regime] = values
    return tables


def _tertile_cutoffs(rows: list[dict[str, object]], quantiles: list[float]) -> tuple[float, float]:
    if not rows:
        raise ValueError("cannot fit M11 tertiles without historical rows")
    values = np.asarray(
        [float(row["features"]["volatility_log_return_20"]) for row in rows],
        dtype=np.float64,
    )
    cutoffs = np.quantile(values, quantiles, method="linear")
    return float(cutoffs[0]), float(cutoffs[1])


def _regime(value: float, cutoffs: tuple[float, float]) -> str:
    if value <= cutoffs[0]:
        return "LOW"
    if value <= cutoffs[1]:
        return "MIDDLE"
    return "HIGH"


def _confusion(labels: np.ndarray, predicted: np.ndarray) -> dict[str, int]:
    return {
        "tn": int(((labels == 0) & (predicted == 0)).sum()),
        "fp": int(((labels == 0) & (predicted == 1)).sum()),
        "fn": int(((labels == 1) & (predicted == 0)).sum()),
        "tp": int(((labels == 1) & (predicted == 1)).sum()),
    }


def _sum_confusion(items: list[dict[str, object]]) -> dict[str, int]:
    return {
        key: sum(int(item["confusion_matrix"][key]) for item in items)
        for key in ("tn", "fp", "fn", "tp")
    }


def _confusion_metrics(confusion: dict[str, int]) -> dict[str, float]:
    tn, fp, fn, tp = (confusion[key] for key in ("tn", "fp", "fn", "tp"))
    total = tn + fp + fn + tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denominator) if denominator else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "mcc": mcc,
        "balanced_accuracy": (recall + specificity) / 2,
        "alert_rate": (tp + fp) / total if total else 0.0,
    }


def _verify_inputs(
    config: dict[str, object],
    feature_dataset: dict[str, object],
    development_dataset: dict[str, object],
    m10_report: dict[str, object],
) -> None:
    if development_dataset["purpose"] != "M10_M11_DEVELOPMENT_SELECTION_ONLY":
        raise ValueError("M11 dataset purpose drifted")
    if development_dataset["feature_dataset_sha256"] != feature_dataset["sha256"]:
        raise ValueError("M11 feature/OOF lineage mismatch")
    if m10_report["development_oof_dataset_sha256"] != development_dataset["sha256"]:
        raise ValueError("M10 report/OOF lineage mismatch")
    if m10_report["result_scope"] != "DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT":
        raise ValueError("M10 report scope drifted")
    if development_dataset["sealed_test_rows_used"] != 0:
        raise ValueError("M11 development dataset contains sealed rows")
    if development_dataset["m7_m8_m9_labels_or_outcomes_used"]:
        raise ValueError("M11 development dataset uses forbidden evidence")
    forbidden = set(config["forbidden_evidence_sha256"])
    if m10_report["analysis_sha256"] in forbidden or development_dataset["sha256"] in forbidden:
        raise ValueError("M11 input is forbidden M7/M8 evidence")
    for row in development_dataset["rows"]:
        _verify_selection_row(row, config)
