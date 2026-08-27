from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from statistics import median
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from pipelines.features.final_study_builder import write_immutable_json, write_report
from research.modeling.final_regressors import (
    MODEL_NAMES,
    FinalRegressionConfig,
    TemporalFitContext,
    canonical_f4_config_sha256,
    fit_candidate,
)
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    OuterFold,
    canonical_config_sha256,
    derive_inner_folds,
)

CONFIG_VERSION = "final-nested-temporal-evaluation-config-v1"
EXPERIMENT_VERSION = "final-nested-temporal-evaluation-v1"
OOF_DATASET_VERSION = "final-regression-oof-predictions-v1"
REPORT_VERSION = "f5-final-nested-temporal-evaluation-report-v1"


class FinalTemporalEvaluationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["final-nested-temporal-evaluation-config-v1"] = CONFIG_VERSION
    experiment_version: Literal["final-nested-temporal-evaluation-v1"] = EXPERIMENT_VERSION
    oof_dataset_version: Literal["final-regression-oof-predictions-v1"] = OOF_DATASET_VERSION
    report_version: Literal["f5-final-nested-temporal-evaluation-report-v1"] = REPORT_VERSION
    f1_protocol_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f4_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outer_fold_names: tuple[str, ...] = Field(min_length=1)
    inner_validation_blocks: Literal[3]
    inner_primary_metric: Literal["spearman"]
    inner_secondary_metric: Literal["mae"]
    inner_tie_breakers: tuple[
        Literal[
            "higher_worst_inner_spearman",
            "lower_model_complexity",
            "lexicographic_parameter_json",
        ],
        ...,
    ]
    outer_metrics: tuple[Literal["mae", "rmse", "r2", "spearman"], ...]
    prediction_quantum: Literal["0.000000000001"]
    minimum_inner_validation_rows: int = Field(ge=1)
    minimum_outer_evaluation_rows: int = Field(ge=1)
    constant_prediction_spearman_policy: Literal["ZERO_AND_REPORT"]
    random_split_allowed: Literal[False]
    global_preprocessing_allowed: Literal[False]
    inner_rows_may_use_outer_evaluation: Literal[False]
    outer_evaluation_may_select_hyperparameters: Literal[False]
    final_model_selection_performed_in_f5: Literal[False]
    f6_analysis_performed_in_f5: Literal[False]
    model_artifact_persisted_in_f5: Literal[False]

    @field_validator("outer_metrics")
    @classmethod
    def exact_outer_metrics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = ("mae", "rmse", "r2", "spearman")
        if value != expected:
            raise ValueError("F5 outer metrics drifted")
        return value


@dataclass(frozen=True)
class ParameterEvidence:
    hyperparameters: dict[str, object]
    fold_metrics: list[dict[str, object]]
    mean_spearman: float
    mean_mae: float
    worst_spearman: float


def load_final_temporal_evaluation_config(path: Path) -> FinalTemporalEvaluationConfig:
    return FinalTemporalEvaluationConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_nested_temporal_evaluation(
    config: FinalTemporalEvaluationConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = verify_evaluation_inputs(config, protocol, regression_config, dataset)
    selected_folds = [
        fold for fold in protocol.outer_evaluation.folds if fold.name in config.outer_fold_names
    ]
    if tuple(fold.name for fold in selected_folds) != config.outer_fold_names:
        raise ValueError("F5 outer fold names/order differ from F1")
    all_oof_rows: list[dict[str, object]] = []
    fold_reports = []
    started = time.perf_counter()
    for outer_fold in selected_folds:
        fold_report, fold_oof = _run_outer_fold(
            config,
            protocol,
            regression_config,
            str(dataset["sha256"]),
            rows,
            outer_fold,
        )
        fold_reports.append(fold_report)
        all_oof_rows.extend(fold_oof)
    ordered_oof = sorted(
        all_oof_rows,
        key=lambda row: (
            str(row["outer_fold"]),
            str(row["model_name"]),
            str(row["feature_session"]),
            str(row["ticker"]),
        ),
    )
    verify_oof_rows(ordered_oof, config.outer_fold_names)
    f5_config_sha256 = canonical_f5_config_sha256(config)
    oof_content = {
        "schema_version": config.oof_dataset_version,
        "experiment_version": config.experiment_version,
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "f4_config_sha256": canonical_f4_config_sha256(regression_config),
        "f5_config_sha256": f5_config_sha256,
        "final_dataset_sha256": dataset["sha256"],
        "models": list(MODEL_NAMES),
        "outer_folds": list(config.outer_fold_names),
        "final_model_selected": False,
        "f6_analysis_performed": False,
        "model_artifact_persisted": False,
        "rows": ordered_oof,
    }
    oof_dataset = {**oof_content, "sha256": _hash(oof_content)}
    model_summaries = _model_summaries(fold_reports)
    report = {
        "report_version": config.report_version,
        "passed": True,
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "f4_config_sha256": canonical_f4_config_sha256(regression_config),
        "f5_config_sha256": f5_config_sha256,
        "final_dataset_sha256": dataset["sha256"],
        "oof_dataset_sha256": oof_dataset["sha256"],
        "outer_fold_count": len(selected_folds),
        "model_count": len(MODEL_NAMES),
        "oof_row_count": len(ordered_oof),
        "fold_reports": fold_reports,
        "model_summaries": model_summaries,
        "elapsed_seconds": time.perf_counter() - started,
        "outer_evaluation_used_for_hyperparameter_selection": False,
        "final_model_selected": False,
        "f6_analysis_performed": False,
        "model_artifact_persisted": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return oof_dataset, report


def verify_evaluation_inputs(
    config: FinalTemporalEvaluationConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset: dict[str, object],
) -> list[dict[str, object]]:
    if config.f1_protocol_config_sha256 != canonical_config_sha256(protocol):
        raise ValueError("F5/F1 protocol lineage mismatch")
    if config.f4_config_sha256 != canonical_f4_config_sha256(regression_config):
        raise ValueError("F5/F4 config lineage mismatch")
    if dataset.get("sha256") != config.final_dataset_sha256:
        raise ValueError("F5 dataset differs from frozen F2 lineage")
    content = {key: value for key, value in dataset.items() if key != "sha256"}
    if dataset.get("sha256") != _hash(content):
        raise ValueError("F5 dataset SHA-256 mismatch")
    if dataset.get("preprocessing_fitted") is not False:
        raise ValueError("F5 requires an unfitted dataset")
    if dataset.get("models_trained") is not False:
        raise ValueError("F5 requires an untrained dataset")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("F5 dataset rows are missing")
    return rows


def evaluate_predictions(actual: np.ndarray, predicted: np.ndarray) -> dict[str, object]:
    actual = np.asarray(actual, dtype=np.float64)
    predicted = np.asarray(predicted, dtype=np.float64)
    if actual.shape != predicted.shape or actual.ndim != 1 or len(actual) == 0:
        raise ValueError("metric arrays must be non-empty and aligned")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("metric arrays must be finite")
    spearman, constant = _spearman(actual, predicted)
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
        "spearman": spearman,
        "constant_prediction_spearman_zeroed": constant,
    }


def select_parameter_evidence(
    model_name: str, evidence: list[ParameterEvidence]
) -> ParameterEvidence:
    if not evidence:
        raise ValueError("parameter selection requires evidence")
    return min(
        evidence,
        key=lambda item: (
            -item.mean_spearman,
            item.mean_mae,
            -item.worst_spearman,
            _complexity_key(model_name, item.hyperparameters),
            _canonical_parameters(item.hyperparameters),
        ),
    )


def verify_oof_rows(rows: list[dict[str, object]], fold_names: tuple[str, ...]) -> None:
    seen: set[tuple[str, str, str]] = set()
    allowed_folds = set(fold_names)
    for row in rows:
        identity = (
            str(row["model_name"]),
            str(row["ticker"]),
            str(row["feature_session"]),
        )
        if identity in seen:
            raise ValueError("duplicate cross-fold model/ticker/session OOF prediction")
        seen.add(identity)
        if row.get("outer_fold") not in allowed_folds:
            raise ValueError("OOF row has an unknown outer fold")
        if row.get("model_name") not in MODEL_NAMES:
            raise ValueError("OOF row has an unknown model")
        if not math.isfinite(float(row["prediction"])):
            raise ValueError("OOF prediction is non-finite")
        if float(row["prediction"]) < 0:
            raise ValueError("OOF prediction is negative")


def canonical_f5_config_sha256(config: FinalTemporalEvaluationConfig) -> str:
    return _hash(config.model_dump(mode="json"))


def write_f5_outputs(
    oof_path: Path,
    report_path: Path,
    oof_dataset: dict[str, object],
    report: dict[str, object],
) -> None:
    write_immutable_json(oof_path, oof_dataset)
    write_report(report_path, report)


def _run_outer_fold(
    config: FinalTemporalEvaluationConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset_sha256: str,
    rows: list[dict[str, object]],
    outer_fold: OuterFold,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    outer_training = _training_rows(
        rows,
        outer_fold.train_start,
        outer_fold.train_end,
        outer_fold.evaluation_start,
    )
    outer_evaluation = _period_rows(
        rows,
        outer_fold.evaluation_start,
        outer_fold.evaluation_end,
    )
    if len(outer_evaluation) < config.minimum_outer_evaluation_rows:
        raise ValueError(f"outer evaluation row count is too small: {outer_fold.name}")
    model_reports = []
    oof_rows = []
    for model_name in MODEL_NAMES:
        parameter_evidence = _inner_parameter_evidence(
            config,
            protocol,
            regression_config,
            dataset_sha256,
            rows,
            outer_fold,
            model_name,
        )
        selected = select_parameter_evidence(model_name, parameter_evidence)
        context = TemporalFitContext(
            name=f"{outer_fold.name}_outer_training",
            training_start=outer_fold.train_start,
            training_end=outer_fold.train_end,
            next_validation_or_evaluation_start=outer_fold.evaluation_start,
        )
        candidate = fit_candidate(
            regression_config,
            protocol,
            dataset_sha256,
            outer_training,
            context,
            model_name,
            selected.hyperparameters,
        )
        predictions = _quantize_predictions(
            candidate.predict_rows(outer_evaluation), config.prediction_quantum
        )
        actual = np.asarray(
            [float(row["target"][regression_config.target_field]) for row in outer_evaluation],
            dtype=np.float64,
        )
        metrics = evaluate_predictions(actual, predictions)
        selected_sha256 = _hash(selected.hyperparameters)
        model_reports.append(
            {
                "model_name": model_name,
                "selected_hyperparameters": selected.hyperparameters,
                "selected_hyperparameters_sha256": selected_sha256,
                "inner_selection": {
                    "candidate_count": len(parameter_evidence),
                    "selected_mean_spearman": selected.mean_spearman,
                    "selected_mean_mae": selected.mean_mae,
                    "selected_worst_spearman": selected.worst_spearman,
                    "selected_fold_metrics": selected.fold_metrics,
                    "all_candidate_evidence": [
                        _parameter_evidence_payload(item) for item in parameter_evidence
                    ],
                },
                "outer_fit_manifest_sha256": candidate.manifest["sha256"],
                "outer_metrics": metrics,
                "outer_training_row_count": len(outer_training),
                "outer_evaluation_row_count": len(outer_evaluation),
            }
        )
        for row, prediction in zip(outer_evaluation, predictions, strict=True):
            oof_rows.append(
                {
                    "outer_fold": outer_fold.name,
                    "model_name": model_name,
                    "ticker": row["ticker"],
                    "feature_session": row["feature_session"],
                    "target_session": row["target_session"],
                    "information_cutoff": row["information_cutoff"],
                    "prediction": _format_prediction(prediction, config.prediction_quantum),
                    "realized_target": row["target"][regression_config.target_field],
                    "source_row_sha256": row["row_sha256"],
                    "selected_hyperparameters_sha256": selected_sha256,
                    "outer_fit_manifest_sha256": candidate.manifest["sha256"],
                }
            )
    return (
        {
            "outer_fold": outer_fold.name,
            "training_start": outer_fold.train_start.isoformat(),
            "training_end": outer_fold.train_end.isoformat(),
            "evaluation_start": outer_fold.evaluation_start.isoformat(),
            "evaluation_end": outer_fold.evaluation_end.isoformat(),
            "training_row_count": len(outer_training),
            "evaluation_row_count": len(outer_evaluation),
            "models": model_reports,
        },
        oof_rows,
    )


def _inner_parameter_evidence(
    config: FinalTemporalEvaluationConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset_sha256: str,
    rows: list[dict[str, object]],
    outer_fold: OuterFold,
    model_name: str,
) -> list[ParameterEvidence]:
    inner_folds = derive_inner_folds(protocol, outer_fold)
    if len(inner_folds) != config.inner_validation_blocks:
        raise ValueError("derived inner fold count differs from F5")
    evidence = []
    for parameters in _parameter_grid(protocol, model_name):
        fold_metrics = []
        for inner in inner_folds:
            training = _training_rows(
                rows,
                inner.train_start,
                inner.train_end,
                inner.validation_start,
            )
            validation = _period_rows(rows, inner.validation_start, inner.validation_end)
            if len(validation) < config.minimum_inner_validation_rows:
                raise ValueError(f"inner validation row count is too small: {inner.name}")
            context = TemporalFitContext(
                name=inner.name,
                training_start=inner.train_start,
                training_end=inner.train_end,
                next_validation_or_evaluation_start=inner.validation_start,
            )
            candidate = fit_candidate(
                regression_config,
                protocol,
                dataset_sha256,
                training,
                context,
                model_name,
                parameters,
            )
            predicted = _quantize_predictions(
                candidate.predict_rows(validation), config.prediction_quantum
            )
            actual = np.asarray(
                [float(row["target"][regression_config.target_field]) for row in validation],
                dtype=np.float64,
            )
            metrics = evaluate_predictions(actual, predicted)
            fold_metrics.append(
                {
                    "inner_fold": inner.name,
                    "training_row_count": len(training),
                    "validation_row_count": len(validation),
                    "mae": metrics["mae"],
                    "spearman": metrics["spearman"],
                    "constant_prediction_spearman_zeroed": metrics[
                        "constant_prediction_spearman_zeroed"
                    ],
                }
            )
        evidence.append(
            ParameterEvidence(
                hyperparameters=parameters,
                fold_metrics=fold_metrics,
                mean_spearman=float(np.mean([item["spearman"] for item in fold_metrics])),
                mean_mae=float(np.mean([item["mae"] for item in fold_metrics])),
                worst_spearman=float(min(item["spearman"] for item in fold_metrics)),
            )
        )
    return evidence


def _training_rows(
    rows: list[dict[str, object]],
    start: date,
    end: date,
    next_period_start: date,
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if start <= date.fromisoformat(str(row["feature_session"])) <= end
        and date.fromisoformat(str(row["target_session"])) < next_period_start
    ]


def _period_rows(
    rows: list[dict[str, object]], start: date, end: date
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if start <= date.fromisoformat(str(row["feature_session"])) <= end
    ]


def _parameter_grid(
    protocol: FinalStudyProtocolConfig, model_name: str
) -> list[dict[str, object]]:
    spec = next(model for model in protocol.models if model.name == model_name)
    if not spec.hyperparameters:
        return [{}]
    names = sorted(spec.hyperparameters)
    choices = []
    for name in names:
        values = spec.hyperparameters[name]
        if not isinstance(values, list) or not values:
            raise ValueError(f"invalid F1 parameter grid: {model_name}.{name}")
        choices.append(values)
    return [dict(zip(names, values, strict=True)) for values in itertools.product(*choices)]


def _complexity_key(model_name: str, parameters: dict[str, object]) -> tuple[object, ...]:
    if model_name == "normalized_move_persistence":
        return (0,)
    if model_name == "ridge_regression":
        return (-float(parameters["alpha"]),)
    return (
        int(parameters["max_leaf_nodes"]),
        -int(parameters["min_samples_leaf"]),
        float(parameters["learning_rate"]),
        -float(parameters["l2_regularization"]),
        int(parameters["max_iter"]),
    )


def _canonical_parameters(parameters: dict[str, object]) -> str:
    return json.dumps(parameters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _spearman(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, bool]:
    actual_ranks = _average_ranks(actual)
    predicted_ranks = _average_ranks(predicted)
    if np.std(actual_ranks) == 0 or np.std(predicted_ranks) == 0:
        return 0.0, True
    value = float(np.corrcoef(actual_ranks, predicted_ranks)[0, 1])
    if not math.isfinite(value):
        return 0.0, True
    return value, False


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end - 1) / 2 + 1
        ranks[order[start:end]] = rank
        start = end
    return ranks


def _quantize_predictions(values: np.ndarray, quantum: str) -> np.ndarray:
    return np.asarray(
        [float(_format_prediction(value, quantum)) for value in values],
        dtype=np.float64,
    )


def _format_prediction(value: object, quantum: str) -> str:
    decimal_value = Decimal(str(float(value)))
    return format(decimal_value.quantize(Decimal(quantum), rounding=ROUND_HALF_EVEN), "f")


def _parameter_evidence_payload(item: ParameterEvidence) -> dict[str, object]:
    return {
        "hyperparameters": item.hyperparameters,
        "fold_metrics": item.fold_metrics,
        "mean_spearman": item.mean_spearman,
        "mean_mae": item.mean_mae,
        "worst_spearman": item.worst_spearman,
    }


def _model_summaries(fold_reports: list[dict[str, object]]) -> dict[str, object]:
    output = {}
    for model_name in MODEL_NAMES:
        metrics = [
            next(model for model in fold["models"] if model["model_name"] == model_name)[
                "outer_metrics"
            ]
            for fold in fold_reports
        ]
        output[model_name] = {
            "fold_count": len(metrics),
            "mean_mae": float(np.mean([item["mae"] for item in metrics])),
            "median_mae": float(median(item["mae"] for item in metrics)),
            "mean_rmse": float(np.mean([item["rmse"] for item in metrics])),
            "mean_r2": float(np.mean([item["r2"] for item in metrics])),
            "mean_spearman": float(np.mean([item["spearman"] for item in metrics])),
            "median_spearman": float(median(item["spearman"] for item in metrics)),
            "worst_spearman": float(min(item["spearman"] for item in metrics)),
        }
    return output


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
