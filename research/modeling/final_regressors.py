from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

import numpy as np
import sklearn
from pydantic import BaseModel, ConfigDict, Field
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from pipelines.features.risk_builder import FEATURE_NAMES
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    canonical_config_sha256,
)

CONFIG_VERSION = "final-regression-model-config-v1"
EXPERIMENT_VERSION = "final-regression-candidates-v1"
FIT_MANIFEST_VERSION = "final-regression-fit-manifest-v1"
MODEL_NAMES = (
    "normalized_move_persistence",
    "ridge_regression",
    "hist_gradient_boosting_regressor",
)


class RidgeImplementationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_intercept: Literal[True]
    solver: Literal["auto"]
    tolerance: float = Field(gt=0, le=0.01)
    scaler_with_mean: Literal[True]
    scaler_with_std: Literal[True]


class HGBImplementationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loss: Literal["squared_error"]
    early_stopping: Literal[False]
    validation_fraction_used: Literal[False]


class FinalRegressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["final-regression-model-config-v1"] = CONFIG_VERSION
    experiment_version: Literal["final-regression-candidates-v1"] = EXPERIMENT_VERSION
    fit_manifest_version: Literal["final-regression-fit-manifest-v1"] = FIT_MANIFEST_VERSION
    dataset_version: Literal["final-volatility-surprise-dataset-v1"]
    f1_protocol_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_version: Literal["next_session_stock_normalized_abs_log_return_v1"]
    target_field: Literal["primary"]
    target_transform: Literal["log1p"]
    inverse_transform: Literal["maximum_zero_expm1"]
    feature_names_source: Literal["risk-features-v1"]
    minimum_training_rows: int = Field(ge=1)
    ridge: RidgeImplementationConfig
    hist_gradient_boosting: HGBImplementationConfig
    training_rows_only: Literal[True]
    validation_or_outer_rows_used_for_fitting: Literal[False]
    hyperparameter_selection_performed_in_f4: Literal[False]
    model_artifact_persisted_in_f4: Literal[False]
    random_split_allowed: Literal[False]


class TemporalFitContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    training_start: date
    training_end: date
    next_validation_or_evaluation_start: date

    def validate_dates(self) -> None:
        if not self.training_start <= self.training_end:
            raise ValueError("training dates are reversed")
        if self.training_end >= self.next_validation_or_evaluation_start:
            raise ValueError("training must end before validation/evaluation starts")


class Predictor(Protocol):
    def predict(self, matrix: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class FittedCandidate:
    model_name: str
    model: Predictor | None
    scaler: StandardScaler | None
    minimum_denominator: float
    manifest: dict[str, object]

    def predict_rows(self, rows: list[dict[str, object]]) -> np.ndarray:
        matrix = feature_matrix(rows)
        if self.model_name == "normalized_move_persistence":
            return _persistence_predictions(rows, self.minimum_denominator)
        transformed = self.scaler.transform(matrix) if self.scaler is not None else matrix
        prediction = np.asarray(self.model.predict(transformed), dtype=np.float64)
        original_scale = np.maximum(0.0, np.expm1(prediction))
        if not np.isfinite(original_scale).all():
            raise ValueError("candidate produced non-finite predictions")
        return original_scale


def load_final_regression_config(path: Path) -> FinalRegressionConfig:
    return FinalRegressionConfig.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_f4_config_sha256(config: FinalRegressionConfig) -> str:
    return _hash(config.model_dump(mode="json"))


def fit_candidate(
    config: FinalRegressionConfig,
    protocol: FinalStudyProtocolConfig,
    dataset_sha256: str,
    training_rows: list[dict[str, object]],
    context: TemporalFitContext,
    model_name: str,
    hyperparameters: dict[str, object],
) -> FittedCandidate:
    verify_f4_contract(config, protocol)
    context.validate_dates()
    if model_name not in MODEL_NAMES:
        raise ValueError(f"unsupported F4 model: {model_name}")
    _validate_hyperparameters(protocol, model_name, hyperparameters)
    rows = verify_training_rows(config, protocol, training_rows, context)
    training_rows_sha256 = _hash(rows)
    matrix = feature_matrix(rows)
    target = target_vector(rows, config)
    transformed_target = np.log1p(target)
    scaler: StandardScaler | None = None
    model: Predictor | None = None
    learned_state: dict[str, object]

    if model_name == "normalized_move_persistence":
        learned_state = {
            "fitted_parameters": 0,
            "formula": "abs(return_log_1) / max(volatility_log_return_20, epsilon)",
        }
    elif model_name == "ridge_regression":
        scaler = StandardScaler(
            with_mean=config.ridge.scaler_with_mean,
            with_std=config.ridge.scaler_with_std,
        )
        scaled = scaler.fit_transform(matrix)
        model = Ridge(
            alpha=float(hyperparameters["alpha"]),
            fit_intercept=config.ridge.fit_intercept,
            solver=config.ridge.solver,
            tol=config.ridge.tolerance,
        )
        model.fit(scaled, transformed_target)
        learned_state = {
            "scaler_mean": _float_list(scaler.mean_),
            "scaler_scale": _float_list(scaler.scale_),
            "coefficient": _float_list(model.coef_),
            "intercept": _number(model.intercept_),
        }
    else:
        model = HistGradientBoostingRegressor(
            loss=config.hist_gradient_boosting.loss,
            learning_rate=float(hyperparameters["learning_rate"]),
            max_iter=int(hyperparameters["max_iter"]),
            max_leaf_nodes=int(hyperparameters["max_leaf_nodes"]),
            min_samples_leaf=int(hyperparameters["min_samples_leaf"]),
            l2_regularization=float(hyperparameters["l2_regularization"]),
            early_stopping=config.hist_gradient_boosting.early_stopping,
            random_state=int(hyperparameters["random_state"]),
        )
        model.fit(matrix, transformed_target)
        training_prediction = np.asarray(model.predict(matrix), dtype=np.float64)
        learned_state = {
            "n_iter": int(model.n_iter_),
            "training_prediction_sha256": _array_sha256(training_prediction),
            "training_prediction_mean": _number(training_prediction.mean()),
            "training_prediction_std": _number(training_prediction.std(ddof=0)),
        }

    config_payload = config.model_dump(mode="json")
    manifest_content = {
        "schema_version": config.fit_manifest_version,
        "experiment_version": config.experiment_version,
        "model_name": model_name,
        "hyperparameters": hyperparameters,
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "f4_config_sha256": _hash(config_payload),
        "dataset_sha256": dataset_sha256,
        "feature_names": list(FEATURE_NAMES),
        "target_version": config.target_version,
        "target_transform": config.target_transform,
        "inverse_transform": config.inverse_transform,
        "temporal_fit_context": context.model_dump(mode="json"),
        "training_row_count": len(rows),
        "training_rows_sha256": training_rows_sha256,
        "validation_or_outer_rows_used_for_fitting": False,
        "hyperparameter_selection_performed": False,
        "model_artifact_persisted": False,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "learned_state": learned_state,
        "learned_state_sha256": _hash(learned_state),
    }
    manifest = {**manifest_content, "sha256": _hash(manifest_content)}
    return FittedCandidate(
        model_name=model_name,
        model=model,
        scaler=scaler,
        minimum_denominator=protocol.primary_target.minimum_denominator_exclusive,
        manifest=manifest,
    )


def verify_f4_contract(
    config: FinalRegressionConfig, protocol: FinalStudyProtocolConfig
) -> None:
    if config.f1_protocol_config_sha256 != canonical_config_sha256(protocol):
        raise ValueError("F4 config does not match the frozen F1 protocol")
    if config.target_version != protocol.primary_target.name:
        raise ValueError("F4 target version drifted from F1")
    if tuple(protocol.features.fixed_feature_names) != FEATURE_NAMES:
        raise ValueError("F4 feature order drifted from F1")
    if tuple(model.name for model in protocol.models) != MODEL_NAMES:
        raise ValueError("F4 model set drifted from F1")


def verify_training_rows(
    config: FinalRegressionConfig,
    protocol: FinalStudyProtocolConfig,
    rows: list[dict[str, object]],
    context: TemporalFitContext,
) -> list[dict[str, object]]:
    if len(rows) < config.minimum_training_rows:
        raise ValueError("training row count is below the F4 minimum")
    seen: set[tuple[str, str]] = set()
    verified = []
    for row in rows:
        ticker = str(row["ticker"])
        feature_session = date.fromisoformat(str(row["feature_session"]))
        target_session = date.fromisoformat(str(row["target_session"]))
        identity = (ticker, feature_session.isoformat())
        if identity in seen:
            raise ValueError("duplicate ticker/feature-session training row")
        seen.add(identity)
        if not context.training_start <= feature_session <= context.training_end:
            raise ValueError("row is outside the declared training period")
        if target_session >= context.next_validation_or_evaluation_start:
            raise ValueError("training target overlaps validation/evaluation")
        features = row.get("features")
        if not isinstance(features, dict) or set(features) != set(FEATURE_NAMES):
            raise ValueError("training row differs from the frozen feature contract")
        if set(features) & set(protocol.features.forbidden_feature_names):
            raise ValueError("future/target field entered training features")
        if any(not math.isfinite(float(features[name])) for name in FEATURE_NAMES):
            raise ValueError("training row contains non-finite features")
        target = row.get("target")
        if not isinstance(target, dict) or target.get("target_version") != config.target_version:
            raise ValueError("training row target version mismatch")
        value = float(target[config.target_field])
        if not math.isfinite(value) or value < 0:
            raise ValueError("training target must be finite and non-negative")
        verified.append(row)
    return sorted(verified, key=lambda row: (str(row["feature_session"]), str(row["ticker"])))


def feature_matrix(rows: list[dict[str, object]]) -> np.ndarray:
    matrix = np.asarray(
        [[float(row["features"][name]) for name in FEATURE_NAMES] for row in rows],
        dtype=np.float64,
    )
    if matrix.ndim != 2 or matrix.shape[1] != len(FEATURE_NAMES):
        raise ValueError("invalid candidate feature matrix")
    if not np.isfinite(matrix).all():
        raise ValueError("candidate feature matrix is non-finite")
    return matrix


def target_vector(
    rows: list[dict[str, object]], config: FinalRegressionConfig
) -> np.ndarray:
    values = np.asarray(
        [float(row["target"][config.target_field]) for row in rows],
        dtype=np.float64,
    )
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("candidate target vector must be finite and non-negative")
    return values


def _validate_hyperparameters(
    protocol: FinalStudyProtocolConfig,
    model_name: str,
    hyperparameters: dict[str, object],
) -> None:
    spec = next(model for model in protocol.models if model.name == model_name)
    expected_keys = set(spec.hyperparameters)
    if set(hyperparameters) != expected_keys:
        raise ValueError("candidate hyperparameter keys differ from F1")
    for name, value in hyperparameters.items():
        allowed = spec.hyperparameters[name]
        if not isinstance(allowed, list) or value not in allowed:
            raise ValueError(f"candidate hyperparameter is outside F1 grid: {name}")


def _persistence_predictions(
    rows: list[dict[str, object]], minimum_denominator: float
) -> np.ndarray:
    predictions = np.asarray(
        [
            abs(float(row["features"]["return_log_1"]))
            / max(
                float(row["features"]["volatility_log_return_20"]),
                minimum_denominator,
            )
            for row in rows
        ],
        dtype=np.float64,
    )
    if not np.isfinite(predictions).all():
        raise ValueError("persistence candidate produced non-finite predictions")
    return predictions


def _array_sha256(values: np.ndarray) -> str:
    normalized = np.asarray(values, dtype="<f8")
    return hashlib.sha256(normalized.tobytes(order="C")).hexdigest()


def _float_list(values: np.ndarray) -> list[float]:
    return [_number(value) for value in np.asarray(values, dtype=np.float64)]


def _number(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("learned state contains a non-finite value")
    return 0.0 if result == 0 else result


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
