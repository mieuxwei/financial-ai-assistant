import hashlib
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.baselines import RiskBaselineConfig
from research.modeling.temporal_validation import (
    RiskTemporalValidationConfig,
    run_temporal_validation,
)
from research.modeling.tree_models import RiskTreeModelConfig


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _baseline_config() -> RiskBaselineConfig:
    return RiskBaselineConfig.model_validate(
        {
            "schema_version": "risk-baseline-config-v1",
            "experiment_version": "risk-baselines-v1",
            "feature_dataset_version": "risk-feature-dataset-v1",
            "train_split": "train",
            "evaluation_split": "validation",
            "normal_label": "NORMAL",
            "high_risk_label": "HIGH_RISK",
            "feature_names": list(FEATURE_NAMES),
            "decision_threshold": 0.5,
            "calibration_bins": 5,
            "minimum_training_rows": 20,
            "minimum_validation_rows": 10,
            "minimum_training_positive_rows": 3,
            "scaler_with_mean": True,
            "scaler_with_std": True,
            "logistic": {
                "c": 1.0,
                "l1_ratio": 0.0,
                "solver": "lbfgs",
                "class_weight": "balanced",
                "max_iter": 200,
                "tolerance": 0.000001,
                "random_state": 20260827,
            },
            "sealed_test_allowed": False,
            "validation_used_for_fitting": False,
            "hyperparameter_selection_performed": False,
        }
    )


def _tree_config() -> RiskTreeModelConfig:
    return RiskTreeModelConfig.model_validate(
        {
            "schema_version": "risk-tree-model-config-v1",
            "experiment_version": "risk-tree-models-v1",
            "feature_dataset_version": "risk-feature-dataset-v1",
            "train_split": "train",
            "evaluation_split": "validation",
            "normal_label": "NORMAL",
            "high_risk_label": "HIGH_RISK",
            "feature_names": list(FEATURE_NAMES),
            "decision_threshold": 0.5,
            "calibration_bins": 5,
            "permutation_importance_repeats": 1,
            "permutation_importance_scoring": "average_precision",
            "minimum_training_rows": 20,
            "minimum_validation_rows": 10,
            "minimum_training_positive_rows": 3,
            "random_forest": {
                "n_estimators": 10,
                "criterion": "log_loss",
                "max_depth": 3,
                "min_samples_split": 4,
                "min_samples_leaf": 2,
                "max_features": "sqrt",
                "bootstrap": True,
                "class_weight": "balanced_subsample",
                "n_jobs": 1,
                "random_state": 20260827,
            },
            "hist_gradient_boosting": {
                "loss": "log_loss",
                "learning_rate": 0.1,
                "max_iter": 10,
                "max_leaf_nodes": 7,
                "max_depth": 3,
                "min_samples_leaf": 2,
                "l2_regularization": 1.0,
                "max_features": 1.0,
                "max_bins": 32,
                "early_stopping": False,
                "class_weight": "balanced",
                "random_state": 20260827,
            },
            "preprocessing_fitted": False,
            "validation_used_for_fitting": False,
            "hyperparameter_selection_performed": False,
            "sealed_test_allowed": False,
        }
    )


def _temporal_config() -> RiskTemporalValidationConfig:
    baseline = _baseline_config()
    tree = _tree_config()
    start = date(2020, 1, 1)
    return RiskTemporalValidationConfig.model_validate(
        {
            "schema_version": "risk-temporal-validation-config-v1",
            "protocol_version": "risk-temporal-validation-v1",
            "feature_dataset_version": "risk-feature-dataset-v1",
            "baseline_config_sha256": _hash(baseline.model_dump(mode="json")),
            "tree_model_config_sha256": _hash(tree.model_dump(mode="json")),
            "normal_label": "NORMAL",
            "high_risk_label": "HIGH_RISK",
            "candidate_models": [
                "logistic_regression",
                "random_forest",
                "hist_gradient_boosting",
            ],
            "folds": [
                {
                    "name": "fold_1",
                    "train_end": (start + timedelta(days=59)).isoformat(),
                    "evaluation_start": (start + timedelta(days=60)).isoformat(),
                    "evaluation_end": (start + timedelta(days=89)).isoformat(),
                },
                {
                    "name": "fold_2",
                    "train_end": (start + timedelta(days=89)).isoformat(),
                    "evaluation_start": (start + timedelta(days=90)).isoformat(),
                    "evaluation_end": (start + timedelta(days=119)).isoformat(),
                },
                {
                    "name": "fold_3",
                    "train_end": (start + timedelta(days=119)).isoformat(),
                    "evaluation_start": (start + timedelta(days=120)).isoformat(),
                    "evaluation_end": (start + timedelta(days=149)).isoformat(),
                },
                {
                    "name": "fold_4",
                    "train_end": (start + timedelta(days=149)).isoformat(),
                    "evaluation_start": (start + timedelta(days=150)).isoformat(),
                    "evaluation_end": (start + timedelta(days=179)).isoformat(),
                },
            ],
            "minimum_fold_training_rows": 40,
            "minimum_fold_evaluation_rows": 20,
            "minimum_fold_positive_rows": 3,
            "purge_target_overlap": True,
            "embargo_sessions": 0,
            "calibration_method": "prequential_platt_or_identity",
            "platt_c": 1.0,
            "probability_clip": 0.000001,
            "calibration_bins": 5,
            "model_selection_primary": "mean_fold_pr_auc",
            "model_selection_secondary": "mean_fold_mcc",
            "calibration_selection_metric": "pooled_prequential_brier",
            "minimum_calibration_brier_improvement": 0.0,
            "threshold_candidates": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            "minimum_high_risk_recall": 0.5,
            "threshold_selection_metric": "mcc_subject_to_minimum_recall",
            "final_fit_end": (start + timedelta(days=199)).isoformat(),
            "sealed_test_start": (start + timedelta(days=201)).isoformat(),
            "sealed_test_allowed": False,
        }
    )


def _dataset() -> dict[str, object]:
    start = date(2020, 1, 1)
    rows = []
    for index in range(200):
        session = start + timedelta(days=index)
        is_high = index % 5 == 0
        signal = 1.0 if is_high else -0.2
        rows.append(
            {
                "ticker": "2330",
                "feature_session": session.isoformat(),
                "information_cutoff": f"{session.isoformat()}T13:30:00+08:00",
                "features": {
                    name: signal * (feature_index + 1) / 23 + (index % 11) * 0.002
                    for feature_index, name in enumerate(FEATURE_NAMES)
                },
                "split": "train" if index < 150 else "validation",
                "target": {
                    "target_session": (session + timedelta(days=1)).isoformat(),
                    "risk_label": "HIGH_RISK" if is_high else "NORMAL",
                },
            }
        )
    content: dict[str, object] = {
        "schema_version": "risk-feature-dataset-v1",
        "pipeline_version": "risk-features-v1",
        "materialized_splits": ["train", "validation"],
        "sealed_test_features_materialized": False,
        "preprocessing_fitted": False,
        "models_trained": False,
        "rows": rows,
    }
    return {**content, "sha256": _hash(content)}


def _rehash(dataset: dict[str, object]) -> None:
    dataset["sha256"] = _hash({key: value for key, value in dataset.items() if key != "sha256"})


def test_temporal_validation_freezes_candidate_without_test() -> None:
    manifest, report = run_temporal_validation(
        _temporal_config(), _dataset(), _baseline_config(), _tree_config()
    )

    assert len(report["folds"]) == 4
    assert manifest["candidate_recipe_frozen"] is True
    assert manifest["selected_model"] in {
        "logistic_regression",
        "random_forest",
        "hist_gradient_boosting",
    }
    assert manifest["selected_calibration"] in {"platt", "identity"}
    assert manifest["selected_threshold"] in _temporal_config().threshold_candidates
    assert report["sealed_test_features_or_outcomes_opened"] is False
    assert report["sealed_test_evaluations"] == 0
    assert all(
        fold["purged_training_rows_with_overlapping_target"] == 1
        for fold in report["folds"]
    )


def test_future_fold_mutation_cannot_change_earlier_fold_evidence() -> None:
    dataset = _dataset()
    _, before = run_temporal_validation(
        _temporal_config(), dataset, _baseline_config(), _tree_config()
    )
    mutated = deepcopy(dataset)
    row = next(row for row in mutated["rows"] if row["feature_session"] == "2020-06-09")
    row["features"][FEATURE_NAMES[0]] = 999.0
    row["target"]["risk_label"] = "NORMAL"
    _rehash(mutated)

    _, after = run_temporal_validation(
        _temporal_config(), mutated, _baseline_config(), _tree_config()
    )

    assert before["folds"][:3] == after["folds"][:3]
    assert before["folds"][3] != after["folds"][3]


def test_temporal_candidate_manifest_is_deterministic() -> None:
    first, _ = run_temporal_validation(
        _temporal_config(), _dataset(), _baseline_config(), _tree_config()
    )
    second, _ = run_temporal_validation(
        _temporal_config(), _dataset(), _baseline_config(), _tree_config()
    )

    assert first == second


def test_temporal_validation_rejects_sealed_input_and_upstream_drift() -> None:
    sealed = _dataset()
    sealed["sealed_test_features_materialized"] = True
    _rehash(sealed)
    with pytest.raises(ValueError, match="sealed test"):
        run_temporal_validation(
            _temporal_config(), sealed, _baseline_config(), _tree_config()
        )

    drifted = _baseline_config().model_copy(
        update={"decision_threshold": 0.4}
    )
    with pytest.raises(ValueError, match="baseline config hash"):
        run_temporal_validation(
            _temporal_config(), _dataset(), drifted, _tree_config()
        )
