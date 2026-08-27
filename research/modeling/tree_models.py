from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Literal

import numpy as np
import sklearn
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.baselines import (
    RiskBaselineConfig,
    binary_labels,
    feature_matrix,
    verify_feature_dataset,
)
from research.modeling.metrics import (
    binary_classification_metrics,
    uniform_calibration_bins,
)

CONFIG_VERSION = "risk-tree-model-config-v1"
EXPERIMENT_VERSION = "risk-tree-models-v1"
MANIFEST_VERSION = "risk-tree-evaluation-manifest-v1"
REPORT_VERSION = "m5-risk-tree-model-report-v1"


class RandomForestConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_estimators: int = Field(ge=10, le=2000)
    criterion: Literal["log_loss"]
    max_depth: int = Field(ge=2, le=100)
    min_samples_split: int = Field(ge=2)
    min_samples_leaf: int = Field(ge=1)
    max_features: Literal["sqrt"]
    bootstrap: Literal[True]
    class_weight: Literal["balanced_subsample"]
    n_jobs: int
    random_state: int


class HistGradientBoostingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loss: Literal["log_loss"]
    learning_rate: float = Field(gt=0, le=1)
    max_iter: int = Field(ge=10, le=2000)
    max_leaf_nodes: int = Field(ge=2, le=255)
    max_depth: int = Field(ge=2, le=100)
    min_samples_leaf: int = Field(ge=1)
    l2_regularization: float = Field(ge=0)
    max_features: float = Field(gt=0, le=1)
    max_bins: int = Field(ge=2, le=255)
    early_stopping: Literal[False]
    class_weight: Literal["balanced"]
    random_state: int


class RiskTreeModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-tree-model-config-v1"] = CONFIG_VERSION
    experiment_version: Literal["risk-tree-models-v1"] = EXPERIMENT_VERSION
    feature_dataset_version: Literal["risk-feature-dataset-v1"]
    train_split: Literal["train"]
    evaluation_split: Literal["validation"]
    normal_label: Literal["NORMAL"]
    high_risk_label: Literal["HIGH_RISK"]
    feature_names: tuple[str, ...]
    decision_threshold: float
    calibration_bins: int = Field(ge=2, le=50)
    permutation_importance_repeats: int = Field(ge=1, le=20)
    permutation_importance_scoring: Literal["average_precision"]
    minimum_training_rows: int = Field(ge=1)
    minimum_validation_rows: int = Field(ge=1)
    minimum_training_positive_rows: int = Field(ge=1)
    random_forest: RandomForestConfig
    hist_gradient_boosting: HistGradientBoostingConfig
    preprocessing_fitted: Literal[False]
    validation_used_for_fitting: Literal[False]
    hyperparameter_selection_performed: Literal[False]
    sealed_test_allowed: Literal[False]

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(value) != FEATURE_NAMES:
            raise ValueError("feature_names must match risk-features-v1")
        return FEATURE_NAMES

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> RiskTreeModelConfig:
        if self.decision_threshold != 0.5:
            raise ValueError("M5 uses the fixed, untuned 0.5 decision threshold")
        return self


def load_risk_tree_model_config(path: Path) -> RiskTreeModelConfig:
    return RiskTreeModelConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_risk_tree_models(
    config: RiskTreeModelConfig,
    feature_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    verification_config = _verification_config(config)
    rows = verify_feature_dataset(verification_config, feature_dataset)
    train_rows = [row for row in rows if row["split"] == config.train_split]
    validation_rows = [row for row in rows if row["split"] == config.evaluation_split]
    if len(train_rows) < config.minimum_training_rows:
        raise ValueError("training row count is below the configured minimum")
    if len(validation_rows) < config.minimum_validation_rows:
        raise ValueError("validation row count is below the configured minimum")

    x_train = feature_matrix(train_rows)
    y_train = binary_labels(train_rows, config.high_risk_label)
    x_validation = feature_matrix(validation_rows)
    y_validation = binary_labels(validation_rows, config.high_risk_label)
    positives = int(y_train.sum())
    if positives < config.minimum_training_positive_rows:
        raise ValueError("training HIGH_RISK row count is below the configured minimum")
    if positives == 0 or positives == len(y_train):
        raise ValueError("training data must contain both risk classes")
    if len(np.unique(y_validation)) != 2:
        raise ValueError("validation evaluation requires both risk classes")

    models = {
        "random_forest": RandomForestClassifier(**config.random_forest.model_dump()),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            **config.hist_gradient_boosting.model_dump()
        ),
    }
    training_rows_sha256 = _hash(train_rows)
    metrics: dict[str, object] = {}
    calibration: dict[str, object] = {}
    importance: dict[str, object] = {}
    resources: dict[str, object] = {}
    learned_states: dict[str, object] = {}
    for name, model in models.items():
        fit_started = time.perf_counter()
        model.fit(x_train, y_train)
        fit_seconds = time.perf_counter() - fit_started

        inference_started = time.perf_counter()
        positive_index = int(np.where(model.classes_ == 1)[0][0])
        validation_probability = model.predict_proba(x_validation)[:, positive_index]
        inference_seconds = time.perf_counter() - inference_started
        train_probability = model.predict_proba(x_train)[:, positive_index]

        importance_started = time.perf_counter()
        permutation = permutation_importance(
            model,
            x_validation,
            y_validation,
            scoring=config.permutation_importance_scoring,
            n_repeats=config.permutation_importance_repeats,
            random_state=_model_random_state(config, name),
            n_jobs=1,
        )
        importance_seconds = time.perf_counter() - importance_started
        importance[name] = _importance_rows(
            permutation.importances_mean,
            permutation.importances_std,
        )
        metrics[name] = binary_classification_metrics(
            y_validation,
            validation_probability,
            config.decision_threshold,
        )
        calibration[name] = uniform_calibration_bins(
            y_validation,
            validation_probability,
            config.calibration_bins,
        )
        resources[name] = {
            "fit_seconds": fit_seconds,
            "validation_inference_seconds": inference_seconds,
            "validation_permutation_importance_seconds": importance_seconds,
            "training_rows": len(train_rows),
            "validation_rows": len(validation_rows),
            "feature_count": len(FEATURE_NAMES),
        }
        state = {
            "model": name,
            "training_rows_sha256": training_rows_sha256,
            "parameters": model.get_params(deep=False),
            "classes": [int(value) for value in model.classes_],
            "training_probability_sha256": _hash([float(value) for value in train_probability]),
        }
        if name == "random_forest":
            state["native_impurity_feature_importance"] = [
                float(value) for value in model.feature_importances_
            ]
        learned_states[name] = {**state, "model_state_sha256": _hash(state)}

    config_payload = config.model_dump(mode="json")
    manifest_content = {
        "schema_version": MANIFEST_VERSION,
        "experiment_version": config.experiment_version,
        "config": config_payload,
        "config_sha256": _hash(config_payload),
        "feature_dataset_sha256": feature_dataset["sha256"],
        "training_rows_sha256": training_rows_sha256,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "fit_split": "train",
        "evaluation_split": "validation",
        "preprocessing_fitted": False,
        "validation_used_for_fitting": False,
        "sealed_test_used": False,
        "hyperparameter_selection_performed": False,
        "models_serialized": False,
        "learned_states": learned_states,
        "validation_permutation_importance": importance,
    }
    manifest = {**manifest_content, "sha256": _hash(manifest_content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "experiment_version": config.experiment_version,
        "feature_dataset_sha256": feature_dataset["sha256"],
        "config_sha256": manifest_content["config_sha256"],
        "evaluation_manifest_sha256": manifest["sha256"],
        "training_rows_sha256": training_rows_sha256,
        "model_state_sha256": {
            name: state["model_state_sha256"] for name, state in learned_states.items()
        },
        "row_counts": {"train": len(train_rows), "validation": len(validation_rows)},
        "decision_threshold": config.decision_threshold,
        "metrics": metrics,
        "calibration": calibration,
        "validation_permutation_importance": importance,
        "resource_cost": resources,
        "importance_used_for_fitting_or_selection": False,
        "validation_predictions_persisted": False,
        "validation_used_for_fitting": False,
        "sealed_test_features_or_outcomes_opened": False,
        "model_selection_performed": False,
        "manual_labels_used": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return manifest, report


def _verification_config(config: RiskTreeModelConfig) -> RiskBaselineConfig:
    return RiskBaselineConfig.model_validate(
        {
            "schema_version": "risk-baseline-config-v1",
            "experiment_version": "risk-baselines-v1",
            "feature_dataset_version": config.feature_dataset_version,
            "train_split": config.train_split,
            "evaluation_split": config.evaluation_split,
            "normal_label": config.normal_label,
            "high_risk_label": config.high_risk_label,
            "feature_names": list(config.feature_names),
            "decision_threshold": config.decision_threshold,
            "calibration_bins": config.calibration_bins,
            "minimum_training_rows": config.minimum_training_rows,
            "minimum_validation_rows": config.minimum_validation_rows,
            "minimum_training_positive_rows": config.minimum_training_positive_rows,
            "scaler_with_mean": True,
            "scaler_with_std": True,
            "logistic": {
                "c": 1.0,
                "l1_ratio": 0.0,
                "solver": "lbfgs",
                "class_weight": "balanced",
                "max_iter": 100,
                "tolerance": 0.0001,
                "random_state": 0,
            },
            "sealed_test_allowed": False,
            "validation_used_for_fitting": False,
            "hyperparameter_selection_performed": False,
        }
    )


def _model_random_state(config: RiskTreeModelConfig, name: str) -> int:
    if name == "random_forest":
        return config.random_forest.random_state
    return config.hist_gradient_boosting.random_state


def _importance_rows(means: np.ndarray, standard_deviations: np.ndarray) -> list[dict[str, object]]:
    rows = [
        {
            "feature": feature,
            "mean_pr_auc_decrease": float(means[index]),
            "standard_deviation": float(standard_deviations[index]),
        }
        for index, feature in enumerate(FEATURE_NAMES)
    ]
    return sorted(rows, key=lambda row: (-float(row["mean_pr_auc_decrease"]), str(row["feature"])))


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
