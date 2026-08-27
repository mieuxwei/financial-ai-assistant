import hashlib
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.tree_models import RiskTreeModelConfig, run_risk_tree_models


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _config(**overrides: object) -> RiskTreeModelConfig:
    values: dict[str, object] = {
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
            "n_estimators": 20,
            "criterion": "log_loss",
            "max_depth": 4,
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
            "max_iter": 20,
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
    values.update(overrides)
    return RiskTreeModelConfig.model_validate(values)


def _dataset() -> dict[str, object]:
    start = date(2020, 1, 1)
    rows = []
    for index in range(80):
        session = start + timedelta(days=index)
        split = "train" if index < 60 else "validation"
        is_high = index % (5 if split == "train" else 4) == 0
        features = {
            name: (1.5 if is_high else -0.5) * (feature_index + 1) / 23
            + (index % 7) * 0.001
            for feature_index, name in enumerate(FEATURE_NAMES)
        }
        rows.append(
            {
                "ticker": "2330",
                "feature_session": session.isoformat(),
                "information_cutoff": f"{session.isoformat()}T13:30:00+08:00",
                "features": features,
                "split": split,
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


def test_tree_models_use_fixed_fair_contract_without_opening_test() -> None:
    manifest, report = run_risk_tree_models(_config(), _dataset())

    assert manifest["fit_split"] == "train"
    assert manifest["evaluation_split"] == "validation"
    assert manifest["preprocessing_fitted"] is False
    assert manifest["validation_used_for_fitting"] is False
    assert manifest["sealed_test_used"] is False
    assert report["row_counts"] == {"train": 60, "validation": 20}
    assert set(report["metrics"]) == {"random_forest", "hist_gradient_boosting"}
    assert report["model_selection_performed"] is False
    assert report["sealed_test_features_or_outcomes_opened"] is False
    assert all(
        len(rows) == len(FEATURE_NAMES)
        for rows in report["validation_permutation_importance"].values()
    )


def test_validation_mutation_does_not_change_fitted_tree_state() -> None:
    dataset = _dataset()
    manifest_before, report_before = run_risk_tree_models(_config(), dataset)
    mutated = deepcopy(dataset)
    row = next(row for row in mutated["rows"] if row["split"] == "validation")
    row["features"][FEATURE_NAMES[0]] = 999.0
    row["target"]["risk_label"] = "NORMAL"
    _rehash(mutated)

    manifest_after, report_after = run_risk_tree_models(_config(), mutated)

    assert report_before["model_state_sha256"] == report_after["model_state_sha256"]
    assert manifest_before["learned_states"] == manifest_after["learned_states"]
    assert report_before["feature_dataset_sha256"] != report_after["feature_dataset_sha256"]
    assert report_before["metrics"] != report_after["metrics"]


def test_tree_model_manifest_is_deterministic_excluding_resource_timing() -> None:
    first, _ = run_risk_tree_models(_config(), _dataset())
    second, _ = run_risk_tree_models(_config(), _dataset())

    assert first == second


def test_rejects_sealed_test_and_hash_tampering() -> None:
    sealed = _dataset()
    sealed["sealed_test_features_materialized"] = True
    _rehash(sealed)
    with pytest.raises(ValueError, match="sealed test"):
        run_risk_tree_models(_config(), sealed)

    tampered = _dataset()
    tampered["rows"][0]["features"][FEATURE_NAMES[0]] = 123.0
    with pytest.raises(ValueError, match="hash mismatch"):
        run_risk_tree_models(_config(), tampered)


def test_rejects_threshold_tuning_early_stopping_and_feature_changes() -> None:
    with pytest.raises(ValidationError, match="fixed, untuned"):
        _config(decision_threshold=0.4)

    values = _config().model_dump(mode="json")
    values["hist_gradient_boosting"]["early_stopping"] = True
    with pytest.raises(ValidationError, match="early_stopping"):
        RiskTreeModelConfig.model_validate(values)

    with pytest.raises(ValidationError, match="feature_names"):
        _config(feature_names=list(reversed(FEATURE_NAMES)))
