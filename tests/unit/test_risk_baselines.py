import hashlib
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.baselines import RiskBaselineConfig, run_risk_baselines


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _config(**overrides: object) -> RiskBaselineConfig:
    values: dict[str, object] = {
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
            "max_iter": 1000,
            "tolerance": 0.000001,
            "random_state": 20260827,
        },
        "sealed_test_allowed": False,
        "validation_used_for_fitting": False,
        "hyperparameter_selection_performed": False,
    }
    values.update(overrides)
    return RiskBaselineConfig.model_validate(values)


def _dataset() -> dict[str, object]:
    start = date(2020, 1, 1)
    rows = []
    for index in range(80):
        session = start + timedelta(days=index)
        split = "train" if index < 60 else "validation"
        is_high = index % (5 if split == "train" else 4) == 0
        signal = 1.5 if is_high else -0.5
        features = {
            name: signal * (feature_index + 1) / 23 + (index % 7) * 0.001
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


def test_baselines_fit_train_only_and_evaluate_validation_without_test() -> None:
    dataset = _dataset()
    for row in dataset["rows"]:
        row["features"] = dict(reversed(list(row["features"].items())))
    _rehash(dataset)
    model, report = run_risk_baselines(_config(), dataset)

    assert model["fit_split"] == "train"
    assert model["validation_used_for_fitting"] is False
    assert model["sealed_test_used"] is False
    assert report["row_counts"] == {"train": 60, "validation": 20}
    assert report["sealed_test_features_or_outcomes_opened"] is False
    assert report["model_selection_performed"] is False
    assert set(report["metrics"]) == {
        "historical_risk_rate",
        "previous_period_persistence",
        "logistic_regression",
    }
    assert set(report["metrics"]["logistic_regression"]["confusion_matrix"]) == {
        "tn",
        "fp",
        "fn",
        "tp",
    }
    assert len(report["calibration"]["logistic_regression"]) == 5


def test_validation_mutation_cannot_change_fitted_model_state() -> None:
    dataset = _dataset()
    model_before, report_before = run_risk_baselines(_config(), dataset)
    mutated = deepcopy(dataset)
    validation_row = next(row for row in mutated["rows"] if row["split"] == "validation")
    validation_row["features"][FEATURE_NAMES[0]] = 999.0
    validation_row["target"]["risk_label"] = "NORMAL"
    _rehash(mutated)

    model_after, report_after = run_risk_baselines(_config(), mutated)

    assert model_before["model_state_sha256"] == model_after["model_state_sha256"]
    assert model_before["learned_state"] == model_after["learned_state"]
    assert report_before["feature_dataset_sha256"] != report_after["feature_dataset_sha256"]
    assert report_before["metrics"] != report_after["metrics"]


def test_persistence_uses_only_an_exact_previous_target_session() -> None:
    dataset = _dataset()
    first_validation_index = next(
        index for index, row in enumerate(dataset["rows"]) if row["split"] == "validation"
    )
    dataset["rows"][first_validation_index - 1]["target"]["target_session"] = "2019-01-01"
    _rehash(dataset)

    _, report = run_risk_baselines(_config(), dataset)

    assert report["persistence_fallback_count"] == 1


def test_rejects_sealed_test_materialization_and_hash_tampering() -> None:
    sealed = _dataset()
    sealed["sealed_test_features_materialized"] = True
    _rehash(sealed)
    with pytest.raises(ValueError, match="sealed test"):
        run_risk_baselines(_config(), sealed)

    tampered = _dataset()
    tampered["rows"][0]["features"][FEATURE_NAMES[0]] = 123.0
    with pytest.raises(ValueError, match="hash mismatch"):
        run_risk_baselines(_config(), tampered)


def test_rejects_threshold_tuning_or_feature_contract_change() -> None:
    with pytest.raises(ValidationError, match="fixed, untuned"):
        _config(decision_threshold=0.4)
    with pytest.raises(ValidationError, match="feature_names"):
        _config(feature_names=list(reversed(FEATURE_NAMES)))
