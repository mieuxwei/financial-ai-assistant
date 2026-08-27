from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import sklearn
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.metrics import (
    binary_classification_metrics,
    uniform_calibration_bins,
)

CONFIG_VERSION = "risk-baseline-config-v1"
EXPERIMENT_VERSION = "risk-baselines-v1"
MODEL_ARTIFACT_VERSION = "risk-logistic-model-v1"
REPORT_VERSION = "m4-risk-baseline-report-v1"


class LogisticConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    c: float = Field(gt=0)
    l1_ratio: Literal[0.0]
    solver: Literal["lbfgs"]
    class_weight: Literal["balanced"]
    max_iter: int = Field(ge=100, le=10000)
    tolerance: float = Field(gt=0, le=0.01)
    random_state: int


class RiskBaselineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-baseline-config-v1"] = CONFIG_VERSION
    experiment_version: Literal["risk-baselines-v1"] = EXPERIMENT_VERSION
    feature_dataset_version: Literal["risk-feature-dataset-v1"]
    train_split: Literal["train"]
    evaluation_split: Literal["validation"]
    normal_label: Literal["NORMAL"]
    high_risk_label: Literal["HIGH_RISK"]
    feature_names: tuple[str, ...]
    decision_threshold: float
    calibration_bins: int = Field(ge=2, le=50)
    minimum_training_rows: int = Field(ge=1)
    minimum_validation_rows: int = Field(ge=1)
    minimum_training_positive_rows: int = Field(ge=1)
    scaler_with_mean: Literal[True]
    scaler_with_std: Literal[True]
    logistic: LogisticConfig
    sealed_test_allowed: Literal[False]
    validation_used_for_fitting: Literal[False]
    hyperparameter_selection_performed: Literal[False]

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(value) != FEATURE_NAMES:
            raise ValueError("feature_names must match risk-features-v1")
        return FEATURE_NAMES

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> RiskBaselineConfig:
        if self.decision_threshold != 0.5:
            raise ValueError("M4 uses the fixed, untuned 0.5 decision threshold")
        return self


def load_risk_baseline_config(path: Path) -> RiskBaselineConfig:
    return RiskBaselineConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_risk_baselines(
    config: RiskBaselineConfig,
    feature_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = verify_feature_dataset(config, feature_dataset)
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

    prevalence = float(y_train.mean())
    scaler = StandardScaler(
        with_mean=config.scaler_with_mean,
        with_std=config.scaler_with_std,
    )
    x_train_scaled = scaler.fit_transform(x_train)
    x_validation_scaled = scaler.transform(x_validation)
    model = LogisticRegression(
        C=config.logistic.c,
        l1_ratio=config.logistic.l1_ratio,
        solver=config.logistic.solver,
        class_weight=config.logistic.class_weight,
        max_iter=config.logistic.max_iter,
        tol=config.logistic.tolerance,
        random_state=config.logistic.random_state,
    )
    model.fit(x_train_scaled, y_train)
    positive_index = int(np.where(model.classes_ == 1)[0][0])
    logistic_probability = model.predict_proba(x_validation_scaled)[:, positive_index]
    historical_probability = np.full(len(validation_rows), prevalence, dtype=float)
    persistence_probability, persistence_fallback_count = _persistence_probabilities(
        rows,
        validation_rows,
        prevalence,
        config,
    )

    training_rows_sha256 = _hash(train_rows)
    learned_state = {
        "feature_names": list(config.feature_names),
        "training_rows_sha256": training_rows_sha256,
        "scaler_mean": _float_list(scaler.mean_),
        "scaler_scale": _float_list(scaler.scale_),
        "classes": [int(value) for value in model.classes_],
        "coefficient": _float_list(model.coef_[0]),
        "intercept": _float_list(model.intercept_),
        "training_prevalence": prevalence,
    }
    model_state_sha256 = _hash(learned_state)
    config_payload = config.model_dump(mode="json")
    artifact_content = {
        "schema_version": MODEL_ARTIFACT_VERSION,
        "experiment_version": config.experiment_version,
        "config": config_payload,
        "config_sha256": _hash(config_payload),
        "feature_dataset_sha256": feature_dataset["sha256"],
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "fit_split": "train",
        "validation_used_for_fitting": False,
        "sealed_test_used": False,
        "hyperparameter_selection_performed": False,
        "learned_state": learned_state,
        "model_state_sha256": model_state_sha256,
    }
    artifact = {**artifact_content, "sha256": _hash(artifact_content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "experiment_version": config.experiment_version,
        "feature_dataset_sha256": feature_dataset["sha256"],
        "config_sha256": artifact_content["config_sha256"],
        "model_artifact_sha256": artifact["sha256"],
        "model_state_sha256": model_state_sha256,
        "training_rows_sha256": training_rows_sha256,
        "row_counts": {"train": len(train_rows), "validation": len(validation_rows)},
        "training_high_risk_prevalence": prevalence,
        "validation_high_risk_prevalence": float(y_validation.mean()),
        "decision_threshold": config.decision_threshold,
        "persistence_fallback_count": persistence_fallback_count,
        "metrics": {
            "historical_risk_rate": binary_classification_metrics(
                y_validation,
                historical_probability,
                config.decision_threshold,
            ),
            "previous_period_persistence": binary_classification_metrics(
                y_validation,
                persistence_probability,
                config.decision_threshold,
            ),
            "logistic_regression": binary_classification_metrics(
                y_validation,
                logistic_probability,
                config.decision_threshold,
            ),
        },
        "calibration": {
            "historical_risk_rate": uniform_calibration_bins(
                y_validation, historical_probability, config.calibration_bins
            ),
            "previous_period_persistence": uniform_calibration_bins(
                y_validation, persistence_probability, config.calibration_bins
            ),
            "logistic_regression": uniform_calibration_bins(
                y_validation, logistic_probability, config.calibration_bins
            ),
        },
        "validation_predictions_persisted": False,
        "validation_used_for_fitting": False,
        "sealed_test_features_or_outcomes_opened": False,
        "model_selection_performed": False,
        "manual_labels_used": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return artifact, report


def verify_feature_dataset(
    config: RiskBaselineConfig,
    dataset: dict[str, object],
) -> list[dict[str, object]]:
    if dataset.get("schema_version") != config.feature_dataset_version:
        raise ValueError("unexpected feature dataset schema")
    content = {key: value for key, value in dataset.items() if key != "sha256"}
    if dataset.get("sha256") != _hash(content):
        raise ValueError("feature dataset hash mismatch")
    if dataset.get("materialized_splits") != ["train", "validation"]:
        raise ValueError("M4 accepts train and validation splits only")
    if dataset.get("sealed_test_features_materialized") is not False:
        raise ValueError("sealed test features must not be materialized")
    if dataset.get("preprocessing_fitted") is not False:
        raise ValueError("M4 requires an unfitted M3 dataset")
    if dataset.get("models_trained") is not False:
        raise ValueError("M4 requires an untrained M3 dataset")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("feature dataset rows are missing")
    identities: set[tuple[str, str]] = set()
    split_dates: defaultdict[str, list[date]] = defaultdict(list)
    verified: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("feature row must be an object")
        split = row.get("split")
        if split not in {config.train_split, config.evaluation_split}:
            raise ValueError("feature dataset contains a sealed or unknown split")
        ticker = str(row.get("ticker"))
        session = str(row.get("feature_session"))
        identity = (ticker, session)
        if identity in identities:
            raise ValueError("duplicate ticker/feature_session row")
        identities.add(identity)
        split_dates[str(split)].append(date.fromisoformat(session))
        features = row.get("features")
        if (
            not isinstance(features, dict)
            or len(features) != len(FEATURE_NAMES)
            or set(features) != set(FEATURE_NAMES)
        ):
            raise ValueError("feature row does not match the fixed feature contract")
        if any(not math.isfinite(float(features[name])) for name in FEATURE_NAMES):
            raise ValueError("feature row contains null or non-finite values")
        target = row.get("target")
        if not isinstance(target, dict) or target.get("risk_label") not in {
            config.normal_label,
            config.high_risk_label,
        }:
            raise ValueError("feature row has an invalid risk label")
        verified.append(row)
    if max(split_dates["train"]) >= min(split_dates["validation"]):
        raise ValueError("training and validation periods overlap or are reversed")
    return sorted(verified, key=lambda row: (str(row["feature_session"]), str(row["ticker"])))


def feature_matrix(rows: list[dict[str, object]]) -> np.ndarray:
    return np.asarray(
        [[float(row["features"][name]) for name in FEATURE_NAMES] for row in rows],
        dtype=np.float64,
    )


def binary_labels(rows: list[dict[str, object]], high_risk_label: str) -> np.ndarray:
    return np.asarray(
        [int(row["target"]["risk_label"] == high_risk_label) for row in rows],
        dtype=np.int8,
    )


def _persistence_probabilities(
    all_rows: list[dict[str, object]],
    validation_rows: list[dict[str, object]],
    fallback: float,
    config: RiskBaselineConfig,
) -> tuple[np.ndarray, int]:
    previous_by_ticker: dict[str, dict[str, object]] = {}
    probabilities: dict[tuple[str, str], float] = {}
    fallback_count = 0
    for row in all_rows:
        ticker = str(row["ticker"])
        session = str(row["feature_session"])
        previous = previous_by_ticker.get(ticker)
        if row["split"] == config.evaluation_split:
            if previous is not None and previous["target"]["target_session"] == session:
                probability = float(
                    previous["target"]["risk_label"] == config.high_risk_label
                )
            else:
                probability = fallback
                fallback_count += 1
            probabilities[(ticker, session)] = probability
        previous_by_ticker[ticker] = row
    ordered = np.asarray(
        [
            probabilities[(str(row["ticker"]), str(row["feature_session"]))]
            for row in validation_rows
        ],
        dtype=np.float64,
    )
    return ordered, fallback_count


def _float_list(values: np.ndarray) -> list[float]:
    return [float(value) for value in values]


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
