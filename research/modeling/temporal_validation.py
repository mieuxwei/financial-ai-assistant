from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import sklearn
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.baselines import (
    RiskBaselineConfig,
    binary_labels,
    feature_matrix,
    verify_feature_dataset,
)
from research.modeling.metrics import binary_classification_metrics, uniform_calibration_bins
from research.modeling.tree_models import RiskTreeModelConfig

CONFIG_VERSION = "risk-temporal-validation-config-v1"
PROTOCOL_VERSION = "risk-temporal-validation-v1"
MANIFEST_VERSION = "risk-final-candidate-manifest-v1"
REPORT_VERSION = "m6-risk-temporal-validation-report-v1"
MODEL_NAMES = ("logistic_regression", "random_forest", "hist_gradient_boosting")


class TemporalFoldConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    train_end: date
    evaluation_start: date
    evaluation_end: date

    @model_validator(mode="after")
    def validate_dates(self) -> TemporalFoldConfig:
        if self.train_end >= self.evaluation_start:
            raise ValueError("fold training must end before evaluation starts")
        if self.evaluation_start > self.evaluation_end:
            raise ValueError("fold evaluation dates are reversed")
        return self


class RiskTemporalValidationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-temporal-validation-config-v1"] = CONFIG_VERSION
    protocol_version: Literal["risk-temporal-validation-v1"] = PROTOCOL_VERSION
    feature_dataset_version: Literal["risk-feature-dataset-v1"]
    baseline_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_model_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normal_label: Literal["NORMAL"]
    high_risk_label: Literal["HIGH_RISK"]
    candidate_models: tuple[str, ...]
    folds: tuple[TemporalFoldConfig, ...] = Field(min_length=3)
    minimum_fold_training_rows: int = Field(ge=1)
    minimum_fold_evaluation_rows: int = Field(ge=1)
    minimum_fold_positive_rows: int = Field(ge=1)
    purge_target_overlap: Literal[True]
    embargo_sessions: Literal[0]
    calibration_method: Literal["prequential_platt_or_identity"]
    platt_c: float = Field(gt=0)
    probability_clip: float = Field(gt=0, lt=0.1)
    calibration_bins: int = Field(ge=2, le=50)
    model_selection_primary: Literal["mean_fold_pr_auc"]
    model_selection_secondary: Literal["mean_fold_mcc"]
    calibration_selection_metric: Literal["pooled_prequential_brier"]
    minimum_calibration_brier_improvement: float = Field(ge=0)
    threshold_candidates: tuple[float, ...] = Field(min_length=2)
    minimum_high_risk_recall: float = Field(gt=0, le=1)
    threshold_selection_metric: Literal["mcc_subject_to_minimum_recall"]
    final_fit_end: date
    sealed_test_start: date
    sealed_test_allowed: Literal[False]

    @field_validator("candidate_models")
    @classmethod
    def validate_models(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(value) != MODEL_NAMES:
            raise ValueError("M6 candidate_models must match the frozen M4/M5 set")
        return MODEL_NAMES

    @field_validator("threshold_candidates")
    @classmethod
    def validate_thresholds(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(not 0 < threshold < 1 for threshold in value):
            raise ValueError("threshold candidates must be inside (0, 1)")
        if tuple(sorted(set(value))) != value:
            raise ValueError("threshold candidates must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_temporal_contract(self) -> RiskTemporalValidationConfig:
        names = [fold.name for fold in self.folds]
        if len(names) != len(set(names)):
            raise ValueError("fold names must be unique")
        for previous, current in zip(self.folds, self.folds[1:], strict=False):
            if previous.evaluation_end >= current.evaluation_start:
                raise ValueError("fold evaluation periods must be ordered and non-overlapping")
            if previous.train_end >= current.train_end:
                raise ValueError("expanding fold train_end values must increase")
        if self.folds[-1].evaluation_end > self.final_fit_end:
            raise ValueError("final fit must include the last evaluation period")
        if self.final_fit_end >= self.sealed_test_start:
            raise ValueError("final fit must end before sealed test starts")
        return self


def load_risk_temporal_validation_config(path: Path) -> RiskTemporalValidationConfig:
    return RiskTemporalValidationConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_temporal_validation(
    config: RiskTemporalValidationConfig,
    feature_dataset: dict[str, object],
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
) -> tuple[dict[str, object], dict[str, object]]:
    _verify_upstream_configs(config, baseline_config, tree_config)
    rows = verify_feature_dataset(baseline_config, feature_dataset)
    if any(
        date.fromisoformat(str(row["feature_session"])) >= config.sealed_test_start
        for row in rows
    ):
        raise ValueError("M6 input contains a sealed-test feature session")

    raw_predictions: defaultdict[str, list[np.ndarray]] = defaultdict(list)
    fold_labels: list[np.ndarray] = []
    fold_reports: list[dict[str, object]] = []
    resources: defaultdict[str, list[float]] = defaultdict(list)
    for fold in config.folds:
        train_rows, evaluation_rows = _fold_rows(rows, fold)
        _verify_fold_rows(config, fold, train_rows, evaluation_rows)
        x_train = feature_matrix(train_rows)
        y_train = binary_labels(train_rows, config.high_risk_label)
        x_evaluation = feature_matrix(evaluation_rows)
        y_evaluation = binary_labels(evaluation_rows, config.high_risk_label)
        fold_labels.append(y_evaluation)
        model_results: dict[str, object] = {}
        for model_name in MODEL_NAMES:
            started = time.perf_counter()
            probabilities, state = fit_predict_candidate(
                model_name,
                x_train,
                y_train,
                x_evaluation,
                baseline_config,
                tree_config,
            )
            elapsed = time.perf_counter() - started
            resources[model_name].append(elapsed)
            raw_predictions[model_name].append(probabilities)
            model_results[model_name] = {
                "metrics_at_0_5": binary_classification_metrics(y_evaluation, probabilities, 0.5),
                "calibration": uniform_calibration_bins(
                    y_evaluation, probabilities, config.calibration_bins
                ),
                "fold_model_state_sha256": _hash(state),
            }
        fold_reports.append(
            {
                "fold": fold.name,
                "train_end": fold.train_end.isoformat(),
                "evaluation_start": fold.evaluation_start.isoformat(),
                "evaluation_end": fold.evaluation_end.isoformat(),
                "training_rows": len(train_rows),
                "evaluation_rows": len(evaluation_rows),
                "evaluation_high_risk_rows": int(y_evaluation.sum()),
                "purged_training_rows_with_overlapping_target": _purged_count(rows, fold),
                "models": model_results,
            }
        )

    selection_scores = _model_selection_scores(fold_reports)
    selected_model = max(
        MODEL_NAMES,
        key=lambda name: (
            float(selection_scores[name]["mean_fold_pr_auc"]),
            float(selection_scores[name]["mean_fold_mcc"]),
            -float(selection_scores[name]["mean_fold_brier"]),
            -MODEL_NAMES.index(name),
        ),
    )
    prequential = _prequential_calibration(config, raw_predictions, fold_labels)
    calibration_evidence = prequential[selected_model]["aggregate"]
    raw_brier = float(calibration_evidence["raw_metrics_at_0_5"]["brier_score"])
    platt_brier = float(calibration_evidence["platt_metrics_at_0_5"]["brier_score"])
    coefficient_is_positive = bool(calibration_evidence["all_platt_coefficients_positive"])
    calibration_method = (
        "platt"
        if coefficient_is_positive
        and raw_brier - platt_brier >= config.minimum_calibration_brier_improvement
        else "identity"
    )
    selection_probabilities = np.concatenate(
        prequential[selected_model]["platt_probabilities"]
        if calibration_method == "platt"
        else raw_predictions[selected_model][1:]
    )
    selection_labels = np.concatenate(fold_labels[1:])
    threshold, threshold_evidence = _select_threshold(
        selection_labels,
        selection_probabilities,
        config,
    )

    final_rows = [
        row
        for row in rows
        if date.fromisoformat(str(row["feature_session"])) <= config.final_fit_end
        and date.fromisoformat(str(row["target"]["target_session"])) < config.sealed_test_start
    ]
    if len(final_rows) != len(rows):
        raise ValueError("M6 final-fit boundary does not exactly cover the pre-test dataset")
    final_x = feature_matrix(final_rows)
    final_y = binary_labels(final_rows, config.high_risk_label)
    final_probability, final_model_state = fit_predict_candidate(
        selected_model,
        final_x,
        final_y,
        final_x,
        baseline_config,
        tree_config,
    )
    final_calibrator = None
    if calibration_method == "platt":
        all_oof_probability = np.concatenate(raw_predictions[selected_model])
        all_oof_labels = np.concatenate(fold_labels)
        final_calibrator = _fit_platt(all_oof_probability, all_oof_labels, config)
    final_fit_rows_sha256 = _hash(final_rows)
    config_payload = config.model_dump(mode="json")
    manifest_content = {
        "schema_version": MANIFEST_VERSION,
        "protocol_version": config.protocol_version,
        "config": config_payload,
        "config_sha256": _hash(config_payload),
        "feature_dataset_sha256": feature_dataset["sha256"],
        "baseline_config_sha256": config.baseline_config_sha256,
        "tree_model_config_sha256": config.tree_model_config_sha256,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "selected_model": selected_model,
        "selected_calibration": calibration_method,
        "selected_threshold": threshold,
        "selection_fold_names": [fold.name for fold in config.folds],
        "selection_excludes_first_fold_for_calibration_and_threshold": True,
        "final_fit_end": config.final_fit_end.isoformat(),
        "final_fit_rows": len(final_rows),
        "final_fit_rows_sha256": final_fit_rows_sha256,
        "final_model_state": final_model_state,
        "final_model_state_sha256": _hash(final_model_state),
        "final_training_probability_sha256": _hash([float(value) for value in final_probability]),
        "final_calibrator": final_calibrator,
        "models_serialized": False,
        "candidate_recipe_frozen": True,
        "sealed_test_features_or_outcomes_opened": False,
        "sealed_test_evaluations": 0,
        "manual_labels_used": False,
    }
    manifest = {**manifest_content, "sha256": _hash(manifest_content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "protocol_version": config.protocol_version,
        "feature_dataset_sha256": feature_dataset["sha256"],
        "config_sha256": manifest_content["config_sha256"],
        "candidate_manifest_sha256": manifest["sha256"],
        "folds": fold_reports,
        "model_selection_scores": selection_scores,
        "prequential_calibration": {
            name: {
                "folds": value["folds"],
                "aggregate": value["aggregate"],
            }
            for name, value in prequential.items()
        },
        "selected_model": selected_model,
        "selected_calibration": calibration_method,
        "calibration_selection_evidence": calibration_evidence,
        "selected_threshold": threshold,
        "threshold_selection_evidence": threshold_evidence,
        "resource_cost_seconds": {
            name: {
                "fold_fit_and_inference_total": sum(values),
                "fold_fit_and_inference_mean": sum(values) / len(values),
            }
            for name, values in resources.items()
        },
        "candidate_recipe_frozen": True,
        "validation_predictions_persisted": False,
        "sealed_test_features_or_outcomes_opened": False,
        "sealed_test_evaluations": 0,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return manifest, report


def _verify_upstream_configs(
    config: RiskTemporalValidationConfig,
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
) -> None:
    if _hash(baseline_config.model_dump(mode="json")) != config.baseline_config_sha256:
        raise ValueError("M4 baseline config hash does not match the frozen M6 contract")
    if _hash(tree_config.model_dump(mode="json")) != config.tree_model_config_sha256:
        raise ValueError("M5 tree config hash does not match the frozen M6 contract")
    if tuple(baseline_config.feature_names) != FEATURE_NAMES:
        raise ValueError("M4 feature contract mismatch")
    if tuple(tree_config.feature_names) != FEATURE_NAMES:
        raise ValueError("M5 feature contract mismatch")


def _fold_rows(
    rows: list[dict[str, object]], fold: TemporalFoldConfig
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    train_rows = [
        row
        for row in rows
        if date.fromisoformat(str(row["feature_session"])) <= fold.train_end
        and date.fromisoformat(str(row["target"]["target_session"])) < fold.evaluation_start
    ]
    evaluation_rows = [
        row
        for row in rows
        if fold.evaluation_start
        <= date.fromisoformat(str(row["feature_session"]))
        <= fold.evaluation_end
    ]
    return train_rows, evaluation_rows


def _purged_count(rows: list[dict[str, object]], fold: TemporalFoldConfig) -> int:
    return sum(
        1
        for row in rows
        if date.fromisoformat(str(row["feature_session"])) <= fold.train_end
        and date.fromisoformat(str(row["target"]["target_session"])) >= fold.evaluation_start
    )


def _verify_fold_rows(
    config: RiskTemporalValidationConfig,
    fold: TemporalFoldConfig,
    train_rows: list[dict[str, object]],
    evaluation_rows: list[dict[str, object]],
) -> None:
    if len(train_rows) < config.minimum_fold_training_rows:
        raise ValueError(f"{fold.name} training rows are below minimum")
    if len(evaluation_rows) < config.minimum_fold_evaluation_rows:
        raise ValueError(f"{fold.name} evaluation rows are below minimum")
    train_labels = binary_labels(train_rows, config.high_risk_label)
    evaluation_labels = binary_labels(evaluation_rows, config.high_risk_label)
    if int(train_labels.sum()) < config.minimum_fold_positive_rows:
        raise ValueError(f"{fold.name} training positives are below minimum")
    if int(evaluation_labels.sum()) < config.minimum_fold_positive_rows:
        raise ValueError(f"{fold.name} evaluation positives are below minimum")
    if max(date.fromisoformat(str(row["target"]["target_session"])) for row in train_rows) >= min(
        date.fromisoformat(str(row["feature_session"])) for row in evaluation_rows
    ):
        raise ValueError(f"{fold.name} target overlap was not purged")


def fit_predict_candidate(
    name: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_evaluation: np.ndarray,
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
) -> tuple[np.ndarray, dict[str, object]]:
    scaler = None
    if name == "logistic_regression":
        scaler = StandardScaler(
            with_mean=baseline_config.scaler_with_mean,
            with_std=baseline_config.scaler_with_std,
        )
        transformed_train = scaler.fit_transform(x_train)
        transformed_evaluation = scaler.transform(x_evaluation)
        model = LogisticRegression(
            C=baseline_config.logistic.c,
            l1_ratio=baseline_config.logistic.l1_ratio,
            solver=baseline_config.logistic.solver,
            class_weight=baseline_config.logistic.class_weight,
            max_iter=baseline_config.logistic.max_iter,
            tol=baseline_config.logistic.tolerance,
            random_state=baseline_config.logistic.random_state,
        )
    elif name == "random_forest":
        transformed_train = x_train
        transformed_evaluation = x_evaluation
        model = RandomForestClassifier(**tree_config.random_forest.model_dump())
    elif name == "hist_gradient_boosting":
        transformed_train = x_train
        transformed_evaluation = x_evaluation
        model = HistGradientBoostingClassifier(
            **tree_config.hist_gradient_boosting.model_dump()
        )
    else:
        raise ValueError(f"unknown candidate model: {name}")
    model.fit(transformed_train, y_train)
    positive_index = int(np.where(model.classes_ == 1)[0][0])
    probabilities = model.predict_proba(transformed_evaluation)[:, positive_index]
    state: dict[str, object] = {
        "model": name,
        "parameters": model.get_params(deep=False),
        "classes": [int(value) for value in model.classes_],
    }
    if scaler is not None:
        state["scaler_mean"] = [float(value) for value in scaler.mean_]
        state["scaler_scale"] = [float(value) for value in scaler.scale_]
        state["coefficient"] = [float(value) for value in model.coef_[0]]
        state["intercept"] = [float(value) for value in model.intercept_]
    elif name == "random_forest":
        state["native_impurity_feature_importance"] = [
            float(value) for value in model.feature_importances_
        ]
    state["evaluation_probability_sha256"] = _hash([float(value) for value in probabilities])
    return probabilities, state


def _model_selection_scores(fold_reports: list[dict[str, object]]) -> dict[str, object]:
    scores = {}
    for name in MODEL_NAMES:
        metrics = [fold["models"][name]["metrics_at_0_5"] for fold in fold_reports]
        scores[name] = {
            "mean_fold_pr_auc": float(np.mean([value["pr_auc"] for value in metrics])),
            "mean_fold_mcc": float(np.mean([value["mcc"] for value in metrics])),
            "mean_fold_brier": float(np.mean([value["brier_score"] for value in metrics])),
            "mean_fold_high_risk_recall": float(
                np.mean([value["recall_high_risk"] for value in metrics])
            ),
        }
    return scores


def _prequential_calibration(
    config: RiskTemporalValidationConfig,
    raw_predictions: dict[str, list[np.ndarray]],
    fold_labels: list[np.ndarray],
) -> dict[str, dict[str, object]]:
    result = {}
    for name in MODEL_NAMES:
        calibrated_probabilities = []
        fold_evidence = []
        coefficients = []
        for index in range(1, len(config.folds)):
            prior_probability = np.concatenate(raw_predictions[name][:index])
            prior_labels = np.concatenate(fold_labels[:index])
            calibrator = _fit_platt(prior_probability, prior_labels, config)
            coefficients.append(float(calibrator["coefficient"]))
            current_probability = _apply_platt(
                raw_predictions[name][index],
                calibrator,
                config.probability_clip,
            )
            calibrated_probabilities.append(current_probability)
            fold_evidence.append(
                {
                    "fold": config.folds[index].name,
                    "calibration_fit_fold_names": [fold.name for fold in config.folds[:index]],
                    "coefficient": calibrator["coefficient"],
                    "intercept": calibrator["intercept"],
                    "metrics_at_0_5": binary_classification_metrics(
                        fold_labels[index], current_probability, 0.5
                    ),
                }
            )
        pooled_labels = np.concatenate(fold_labels[1:])
        pooled_raw = np.concatenate(raw_predictions[name][1:])
        pooled_platt = np.concatenate(calibrated_probabilities)
        result[name] = {
            "folds": fold_evidence,
            "platt_probabilities": calibrated_probabilities,
            "aggregate": {
                "evaluation_fold_names": [fold.name for fold in config.folds[1:]],
                "raw_metrics_at_0_5": binary_classification_metrics(
                    pooled_labels, pooled_raw, 0.5
                ),
                "platt_metrics_at_0_5": binary_classification_metrics(
                    pooled_labels, pooled_platt, 0.5
                ),
                "all_platt_coefficients_positive": all(value > 0 for value in coefficients),
            },
        }
    return result


def _fit_platt(
    probabilities: np.ndarray,
    labels: np.ndarray,
    config: RiskTemporalValidationConfig,
) -> dict[str, float]:
    logits = _logits(probabilities, config.probability_clip).reshape(-1, 1)
    calibrator = LogisticRegression(
        C=config.platt_c,
        l1_ratio=0.0,
        solver="lbfgs",
        max_iter=1000,
        tol=1e-8,
        random_state=0,
    )
    calibrator.fit(logits, labels)
    return {
        "coefficient": float(calibrator.coef_[0][0]),
        "intercept": float(calibrator.intercept_[0]),
        "fit_rows": len(labels),
        "fit_probability_sha256": _hash([float(value) for value in probabilities]),
        "fit_labels_sha256": _hash([int(value) for value in labels]),
    }


def _apply_platt(
    probabilities: np.ndarray,
    calibrator: dict[str, float],
    clip: float,
) -> np.ndarray:
    values = calibrator["coefficient"] * _logits(probabilities, clip) + calibrator["intercept"]
    return 1.0 / (1.0 + np.exp(-values))


def _logits(probabilities: np.ndarray, clip: float) -> np.ndarray:
    clipped = np.clip(probabilities, clip, 1 - clip)
    return np.log(clipped / (1 - clipped))


def _select_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
    config: RiskTemporalValidationConfig,
) -> tuple[float, dict[str, object]]:
    candidates = []
    for threshold in config.threshold_candidates:
        metrics = binary_classification_metrics(labels, probabilities, threshold)
        candidates.append({"threshold": threshold, "metrics": metrics})
    eligible = [
        item
        for item in candidates
        if float(item["metrics"]["recall_high_risk"]) >= config.minimum_high_risk_recall
    ]
    if not eligible:
        raise ValueError("no threshold candidate satisfies minimum HIGH_RISK recall")
    selected = max(
        eligible,
        key=lambda item: (
            float(item["metrics"]["mcc"]),
            float(item["metrics"]["precision_high_risk"]),
            -abs(float(item["threshold"]) - 0.5),
            -float(item["threshold"]),
        ),
    )
    return float(selected["threshold"]), {
        "minimum_high_risk_recall": config.minimum_high_risk_recall,
        "eligible_threshold_count": len(eligible),
        "selected_metrics": selected["metrics"],
        "candidate_count": len(candidates),
    }


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
