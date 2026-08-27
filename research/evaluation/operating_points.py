from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np

from research.modeling.baselines import (
    RiskBaselineConfig,
    binary_labels,
    feature_matrix,
    verify_feature_dataset,
)
from research.modeling.metrics import binary_classification_metrics, uniform_calibration_bins
from research.modeling.temporal_validation import (
    RiskTemporalValidationConfig,
    _apply_platt,
    _fit_platt,
    _fold_rows,
    _verify_fold_rows,
    fit_predict_candidate,
)
from research.modeling.tree_models import RiskTreeModelConfig

DATASET_VERSION = "post-m8-development-oof-dataset-v1"
ANALYSIS_VERSION = "post-m8-operating-point-analysis-v1"
REPORT_VERSION = "m10-operating-point-report-v1"


def load_config(path: Path) -> dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config["schema_version"] != "post-m8-operating-point-config-v1":
        raise ValueError("unexpected M10 config schema")
    if config["status"] != "PROTOCOL_FROZEN_SEARCH_NOT_RUN":
        raise ValueError("M10 protocol status drifted")
    source = config["development_prediction_source"]
    if source["allowed_splits"] != ["train", "validation"]:
        raise ValueError("M10 source is not development-only")
    if source["latest_allowed_target_session"] != "2024-12-31":
        raise ValueError("M10 development cutoff drifted")
    if source["sealed_test_rows_allowed"] or source["m7_or_m8_labels_allowed"]:
        raise ValueError("M10 permits historical sealed evidence")
    if config["historical_threshold_replacement_allowed"]:
        raise ValueError("M10 permits retrospective threshold replacement")
    return config


def reconstruct_development_oof(
    config: dict[str, object],
    temporal_config: RiskTemporalValidationConfig,
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
    feature_dataset: dict[str, object],
    candidate_manifest: dict[str, object],
    m6_report: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = verify_feature_dataset(baseline_config, feature_dataset)
    _verify_development_lineage(
        config,
        temporal_config,
        feature_dataset,
        candidate_manifest,
        m6_report,
        rows,
    )
    raw_predictions: list[np.ndarray] = []
    fold_labels: list[np.ndarray] = []
    fold_rows: list[list[dict[str, object]]] = []
    fold_evidence = []
    expected_folds = {fold["fold"]: fold for fold in m6_report["folds"]}
    for fold in temporal_config.folds:
        train_rows, evaluation_rows = _fold_rows(rows, fold)
        _verify_fold_rows(temporal_config, fold, train_rows, evaluation_rows)
        probabilities, state = fit_predict_candidate(
            "logistic_regression",
            feature_matrix(train_rows),
            binary_labels(train_rows, temporal_config.high_risk_label),
            feature_matrix(evaluation_rows),
            baseline_config,
            tree_config,
        )
        state_sha256 = _hash(state)
        expected_state = expected_folds[fold.name]["models"]["logistic_regression"][
            "fold_model_state_sha256"
        ]
        if state_sha256 != expected_state:
            raise ValueError(f"{fold.name} Logistic state does not reproduce M6")
        labels = binary_labels(evaluation_rows, temporal_config.high_risk_label)
        raw_predictions.append(probabilities)
        fold_labels.append(labels)
        fold_rows.append(evaluation_rows)
        fold_evidence.append(
            {
                "fold": fold.name,
                "training_rows": len(train_rows),
                "evaluation_rows": len(evaluation_rows),
                "model_state_sha256": state_sha256,
            }
        )

    development_rows = []
    expected_calibration = {
        fold["fold"]: fold
        for fold in m6_report["prequential_calibration"]["logistic_regression"]["folds"]
    }
    for index in range(1, len(temporal_config.folds)):
        calibrator = _fit_platt(
            np.concatenate(raw_predictions[:index]),
            np.concatenate(fold_labels[:index]),
            temporal_config,
        )
        expected = expected_calibration[temporal_config.folds[index].name]
        _assert_close(calibrator["coefficient"], expected["coefficient"], "Platt coefficient")
        _assert_close(calibrator["intercept"], expected["intercept"], "Platt intercept")
        calibrated = _apply_platt(
            raw_predictions[index], calibrator, temporal_config.probability_clip
        )
        for row, probability, label in zip(
            fold_rows[index], calibrated, fold_labels[index], strict=True
        ):
            _verify_selection_row(row, config)
            development_rows.append(
                {
                    "ticker": str(row["ticker"]),
                    "feature_session": str(row["feature_session"]),
                    "target_session": str(row["target"]["target_session"]),
                    "source_split": str(row["split"]),
                    "fold": temporal_config.folds[index].name,
                    "calibrated_probability": float(probability),
                    "high_risk_label": int(label),
                    "volatility_log_return_20": float(
                        row["features"]["volatility_log_return_20"]
                    ),
                }
            )
    development_rows.sort(key=lambda row: (row["feature_session"], row["ticker"]))
    labels = np.asarray([row["high_risk_label"] for row in development_rows], dtype=np.int8)
    probabilities = np.asarray(
        [row["calibrated_probability"] for row in development_rows], dtype=np.float64
    )
    expected_metrics = m6_report["calibration_selection_evidence"]["platt_metrics_at_0_5"]
    reproduced_metrics = binary_classification_metrics(labels, probabilities, 0.5)
    _assert_nested_close(reproduced_metrics, expected_metrics, "M6 pooled Platt metrics")
    dataset_content = {
        "schema_version": DATASET_VERSION,
        "protocol_version": config["protocol_version"],
        "purpose": "M10_M11_DEVELOPMENT_SELECTION_ONLY",
        "m10_config_sha256": _hash(config),
        "m6_temporal_config_sha256": m6_report["config_sha256"],
        "m6_candidate_manifest_sha256": candidate_manifest["sha256"],
        "feature_dataset_sha256": feature_dataset["sha256"],
        "folds": [fold.name for fold in temporal_config.folds[1:]],
        "first_fold_excluded_from_selection": True,
        "row_count": len(development_rows),
        "positive_count": int(labels.sum()),
        "latest_target_session": max(row["target_session"] for row in development_rows),
        "m6_pooled_platt_metrics_at_0_5": reproduced_metrics,
        "fold_reconstruction_evidence": fold_evidence,
        "sealed_test_rows_used": 0,
        "m7_m8_m9_labels_or_outcomes_used": False,
        "m7_final_candidate_refit_performed": False,
        "rows": development_rows,
    }
    dataset = {**dataset_content, "sha256": _hash(dataset_content)}
    evidence = {
        "development_oof_dataset_sha256": dataset["sha256"],
        "row_count": len(development_rows),
        "positive_count": int(labels.sum()),
        "folds": dataset_content["folds"],
        "latest_target_session": dataset_content["latest_target_session"],
        "m6_pooled_platt_metrics_at_0_5": reproduced_metrics,
        "fold_reconstruction_evidence": fold_evidence,
    }
    return dataset, evidence


def analyze_operating_points(
    config: dict[str, object],
    development_dataset: dict[str, object],
    reconstruction_evidence: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    _verify_hash(development_dataset, "M10 development OOF dataset")
    if development_dataset["purpose"] != "M10_M11_DEVELOPMENT_SELECTION_ONLY":
        raise ValueError("M10 dataset purpose drifted")
    if development_dataset["sealed_test_rows_used"] != 0:
        raise ValueError("M10 development dataset contains sealed rows")
    if development_dataset["m7_m8_m9_labels_or_outcomes_used"]:
        raise ValueError("M10 development dataset uses post-M6 evidence")
    rows = development_dataset["rows"]
    for row in rows:
        _verify_selection_row(row, config)
    labels = np.asarray([row["high_risk_label"] for row in rows], dtype=np.int8)
    probabilities = np.asarray(
        [row["calibrated_probability"] for row in rows], dtype=np.float64
    )
    thresholds = _threshold_grid(config["threshold_grid"])
    candidates = [_candidate(labels, probabilities, threshold) for threshold in thresholds]
    modes = {
        name: select_operating_mode(candidates, name, rule)
        for name, rule in config["operating_modes"].items()
    }
    historical = _candidate(labels, probabilities, config["historical_m7_threshold"])
    calibration = uniform_calibration_bins(labels, probabilities, 10)
    content = {
        "schema_version": ANALYSIS_VERSION,
        "protocol_version": config["protocol_version"],
        "config_sha256": _hash(config),
        "development_oof_dataset_sha256": development_dataset["sha256"],
        "development_row_count": len(rows),
        "development_positive_count": int(labels.sum()),
        "development_period_end": max(row["target_session"] for row in rows),
        "reconstruction_evidence": reconstruction_evidence,
        "historical_0.10_development_metrics": historical,
        "operating_modes": modes,
        "calibration_table": calibration,
        "threshold_grid_results": candidates,
        "result_scope": "DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT",
        "historical_threshold_replaced": False,
        "sealed_test_rows_used": 0,
        "m7_m8_m9_labels_or_outcomes_used": False,
        "m7_final_candidate_refit_performed": False,
        "m7_rerun_performed": False,
        "m8_rerun_performed": False,
        "m9_rerun_performed": False,
        "rows_persisted_in_analysis": False,
    }
    analysis = {**content, "sha256": _hash(content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "analysis_sha256": analysis["sha256"],
        **{key: value for key, value in content.items() if key != "threshold_grid_results"},
        "threshold_grid_candidate_count": len(candidates),
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return analysis, report


def select_operating_mode(
    candidates: list[dict[str, object]], name: str, rule: dict[str, object]
) -> dict[str, object]:
    eligible = [item for item in candidates if _meets_constraints(item, rule["constraints"])]
    if not eligible:
        return {
            "status": "INCONCLUSIVE_NO_POLICY_SELECTED",
            "eligible_candidate_count": 0,
            "selected": None,
        }

    def score(item: dict[str, object]) -> tuple[object, ...]:
        if name == "screening":
            return (
                item["recall"],
                item["mcc"],
                item["precision"],
                item["threshold"],
            )
        if name == "balanced":
            return (
                item["mcc"],
                item["f1"],
                item["balanced_accuracy"],
                item["threshold"],
            )
        if name == "precision":
            return (
                item["precision"],
                item["mcc"],
                item["recall"],
                item["threshold"],
            )
        raise ValueError(f"unknown M10 operating mode: {name}")

    return {
        "status": "DEVELOPMENT_POLICY_SELECTED_NOT_HOLDOUT_VALIDATED",
        "eligible_candidate_count": len(eligible),
        "selected": max(eligible, key=score),
    }


def _candidate(
    labels: np.ndarray, probabilities: np.ndarray, threshold: float
) -> dict[str, object]:
    metrics = binary_classification_metrics(labels, probabilities, threshold)
    confusion = metrics["confusion_matrix"]
    predicted_positive = confusion["tp"] + confusion["fp"]
    predicted_positive_rate = predicted_positive / len(labels)
    return {
        "threshold": threshold,
        "precision": metrics["precision_high_risk"],
        "recall": metrics["recall_high_risk"],
        "specificity": metrics["specificity"],
        "f1": metrics["f1_high_risk"],
        "mcc": metrics["mcc"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "predicted_positive_rate": predicted_positive_rate,
        "alerts_per_252_sessions": predicted_positive_rate * 252,
        "confusion_matrix": confusion,
    }


def _meets_constraints(candidate: dict[str, object], constraints: dict[str, object]) -> bool:
    mapping = {
        "minimum_precision": "precision",
        "minimum_recall": "recall",
        "minimum_specificity": "specificity",
    }
    return all(
        float(candidate[mapping[name]]) >= float(value) for name, value in constraints.items()
    )


def _threshold_grid(grid: dict[str, object]) -> list[float]:
    if grid["type"] != "inclusive_decimal_grid":
        raise ValueError("unsupported M10 threshold grid")
    start = round(float(grid["start"]) * 100)
    stop = round(float(grid["stop"]) * 100)
    step = round(float(grid["step"]) * 100)
    if step <= 0 or any(
        abs(value * 100 - round(value * 100)) > 1e-9
        for value in (float(grid["start"]), float(grid["stop"]), float(grid["step"]))
    ):
        raise ValueError("M10 grid must use exact cent increments")
    return [value / 100 for value in range(start, stop + 1, step)]


def _verify_development_lineage(
    config: dict[str, object],
    temporal_config: RiskTemporalValidationConfig,
    feature_dataset: dict[str, object],
    candidate_manifest: dict[str, object],
    m6_report: dict[str, object],
    rows: list[dict[str, object]],
) -> None:
    _verify_hash(feature_dataset, "M3 feature dataset")
    _verify_hash(candidate_manifest, "M6 candidate manifest")
    source = config["development_prediction_source"]
    temporal_hash = _hash(temporal_config.model_dump(mode="json"))
    if temporal_hash != source["risk_temporal_validation_config_sha256"]:
        raise ValueError("M6 temporal config hash does not match M10")
    if m6_report["config_sha256"] != temporal_hash:
        raise ValueError("M6 report/config lineage mismatch")
    if candidate_manifest["sha256"] != source["candidate_manifest_sha256"]:
        raise ValueError("M6 candidate manifest does not match M10")
    if m6_report["candidate_manifest_sha256"] != candidate_manifest["sha256"]:
        raise ValueError("M6 report/manifest lineage mismatch")
    if m6_report["selected_model"] != "logistic_regression":
        raise ValueError("M10 expects the frozen M6 Logistic candidate")
    if m6_report["selected_calibration"] != "platt":
        raise ValueError("M10 expects the frozen M6 Platt calibration")
    if m6_report["selected_threshold"] != config["historical_m7_threshold"]:
        raise ValueError("historical M6/M10 threshold mismatch")
    if any(str(row["split"]) not in source["allowed_splits"] for row in rows):
        raise ValueError("M10 input contains a non-development split")
    if any(
        date.fromisoformat(str(row["target"]["target_session"]))
        > date.fromisoformat(source["latest_allowed_target_session"])
        for row in rows
    ):
        raise ValueError("M10 input reaches beyond the development cutoff")


def _verify_selection_row(row: dict[str, object], config: dict[str, object]) -> None:
    source = config["development_prediction_source"]
    split = str(row.get("source_split", row.get("split")))
    target_session = str(row.get("target_session", row.get("target", {}).get("target_session")))
    if split not in source["allowed_splits"]:
        raise ValueError("threshold selection row is not train/validation")
    if target_session > source["latest_allowed_target_session"]:
        raise ValueError("threshold selection row reaches sealed-test time")


def _assert_close(actual: object, expected: object, name: str) -> None:
    if not math_isclose(float(actual), float(expected)):
        raise ValueError(f"{name} does not reproduce M6")


def _assert_nested_close(actual: object, expected: object, name: str) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{name} keys differ")
        for key in expected:
            _assert_nested_close(actual[key], expected[key], f"{name}.{key}")
    elif isinstance(expected, (int, float)):
        _assert_close(actual, expected, name)
    elif actual != expected:
        raise ValueError(f"{name} differs")


def math_isclose(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-12 * max(1.0, abs(left), abs(right))


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
