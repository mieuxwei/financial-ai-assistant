from __future__ import annotations

import bisect
import hashlib
import json
import math
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipelines.features.final_study_builder import write_immutable_json, write_report
from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.final_regressors import (
    FinalRegressionConfig,
    TemporalFitContext,
    canonical_f4_config_sha256,
    fit_candidate,
)
from research.modeling.final_temporal_evaluation import (
    ParameterEvidence,
    evaluate_predictions,
    select_parameter_evidence,
)
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    canonical_config_sha256,
)

CONFIG_VERSION = "final-model-freeze-config-v1"
ARTIFACT_VERSION = "final-ridge-research-model-v1"
REPORT_VERSION = "f7-final-research-model-report-v1"
INFERENCE_VERSION = "volatility-surprise-inference-v1"
COMPLEXITY_ORDER = {
    "normalized_move_persistence": 0,
    "ridge_regression": 1,
    "hist_gradient_boosting_regressor": 2,
}


class SelectionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: Literal["highest_mean_outer_spearman"]
    practical_tie_margin_spearman: float = Field(gt=0)
    within_tie_preference: tuple[str, ...]
    single_period_or_subgroup_selection_allowed: Literal[False]
    expected_selected_model: Literal["ridge_regression"]


class HyperparameterSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["latest_three_complete_calendar_years_expanding_window"]
    validation_years: tuple[int, int, int]
    training_start: date
    selection_primary: Literal["mean_inner_spearman"]
    selection_secondary: Literal["mean_inner_mae"]
    tie_breakers: tuple[str, ...]
    expected_selected_hyperparameters: dict[str, float]


class FinalFitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    training_feature_start: date
    training_feature_end: date
    training_target_end: date
    next_unseen_session_boundary: date
    use_all_eligible_rows: Literal[True]
    previous_outer_period_rows_included_as_historical_training: Literal[True]
    oof_predictions_or_evaluation_metrics_used_for_fitting: Literal[False]

    @model_validator(mode="after")
    def chronological(self) -> FinalFitConfig:
        if not self.training_feature_start <= self.training_feature_end:
            raise ValueError("F7 final-fit feature dates are reversed")
        if self.training_feature_end > self.training_target_end:
            raise ValueError("F7 target end precedes feature end")
        if self.training_target_end >= self.next_unseen_session_boundary:
            raise ValueError("F7 next unseen boundary must follow training targets")
        return self


class HistoricalReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["selected_model_pooled_historical_outer_oof_predictions"]
    expected_row_count: int = Field(ge=1)
    quantile_method: Literal["linear"]
    percentile_method: Literal["empirical_cdf_right_inclusive"]
    percentile_output_decimals: int = Field(ge=0, le=12)
    band_quantiles: tuple[float, float, float]
    band_labels: tuple[Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"], ...]
    boundary_rule: Literal[
        "LOW_LT_P50_MODERATE_LT_P80_HIGH_LT_P95_VERY_HIGH_GE_P95"
    ]


class FinalModelFreezeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["final-model-freeze-config-v1"] = CONFIG_VERSION
    artifact_version: Literal["final-ridge-research-model-v1"] = ARTIFACT_VERSION
    report_version: Literal["f7-final-research-model-report-v1"] = REPORT_VERSION
    inference_contract_version: Literal["volatility-surprise-inference-v1"] = INFERENCE_VERSION
    f1_protocol_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f4_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f5_oof_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f6_analysis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selection_rule: SelectionRule
    final_hyperparameter_selection: HyperparameterSelection
    final_fit: FinalFitConfig
    historical_reference: HistoricalReference
    prediction_quantum: Literal["0.000000000001"]
    artifact_format: Literal["SAFE_JSON_NO_PICKLE"]
    required_output_fields: tuple[str, ...]
    claim_as_prospective_accuracy: Literal[False]
    direction_forecast: Literal[False]
    investment_advice: Literal[False]
    m7_rerun_allowed: Literal[False]
    deploy_in_f7: Literal[False]

    @model_validator(mode="after")
    def frozen_contract(self) -> FinalModelFreezeConfig:
        expected_preferences = (
            "lower_mean_outer_mae",
            "higher_worst_outer_spearman",
            "lower_implementation_complexity",
        )
        if self.selection_rule.within_tie_preference != expected_preferences:
            raise ValueError("F7 model-selection tie-break drifted")
        if self.selection_rule.practical_tie_margin_spearman != 0.01:
            raise ValueError("F7 practical-tie margin drifted")
        if self.final_hyperparameter_selection.validation_years != (2023, 2024, 2025):
            raise ValueError("F7 final inner validation years drifted")
        if self.final_hyperparameter_selection.expected_selected_hyperparameters != {
            "alpha": 100.0
        }:
            raise ValueError("F7 expected Ridge hyperparameters drifted")
        if self.historical_reference.band_quantiles != (0.5, 0.8, 0.95):
            raise ValueError("F7 band quantiles drifted")
        if self.historical_reference.band_labels != (
            "LOW",
            "MODERATE",
            "HIGH",
            "VERY_HIGH",
        ):
            raise ValueError("F7 band labels drifted")
        return self


def load_final_model_freeze_config(path: Path) -> FinalModelFreezeConfig:
    return FinalModelFreezeConfig.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_f7_config_sha256(config: FinalModelFreezeConfig) -> str:
    return _hash(config.model_dump(mode="json"))


def freeze_final_research_model(
    config: FinalModelFreezeConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset: dict[str, object],
    oof: dict[str, object],
    f6_analysis: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = verify_f7_inputs(
        config, protocol, regression_config, dataset, oof, f6_analysis
    )
    selection = select_final_model(config, f6_analysis)
    if selection["selected_model"] != "ridge_regression":
        raise ValueError("F7 v1 JSON artifact supports the frozen Ridge selection only")
    hyperparameter_evidence = select_final_hyperparameters(
        config, protocol, regression_config, dataset["sha256"], rows
    )
    selected_hyperparameters = hyperparameter_evidence["selected_hyperparameters"]
    expected_hyperparameters = (
        config.final_hyperparameter_selection.expected_selected_hyperparameters
    )
    if selected_hyperparameters != expected_hyperparameters:
        raise ValueError("F7 temporal hyperparameter result differs from frozen expectation")
    training_rows = _final_training_rows(config, rows)
    context = TemporalFitContext(
        name="f7_full_historical_research_fit",
        training_start=config.final_fit.training_feature_start,
        training_end=config.final_fit.training_feature_end,
        next_validation_or_evaluation_start=config.final_fit.next_unseen_session_boundary,
    )
    candidate = fit_candidate(
        regression_config,
        protocol,
        str(dataset["sha256"]),
        training_rows,
        context,
        "ridge_regression",
        selected_hyperparameters,
    )
    repeated = fit_candidate(
        regression_config,
        protocol,
        str(dataset["sha256"]),
        training_rows,
        context,
        "ridge_regression",
        selected_hyperparameters,
    )
    if candidate.manifest["learned_state_sha256"] != repeated.manifest["learned_state_sha256"]:
        raise ValueError("F7 repeated Ridge fit is not deterministic")
    reference = _historical_reference(config, oof, "ridge_regression")
    learned_state = candidate.manifest["learned_state"]
    artifact_content = {
        "schema_version": config.artifact_version,
        "inference_contract_version": config.inference_contract_version,
        "artifact_format": config.artifact_format,
        "model_name": "ridge_regression",
        "model_version": config.artifact_version,
        "feature_pipeline_version": dataset["feature_pipeline_version"],
        "feature_names": list(FEATURE_NAMES),
        "target_version": regression_config.target_version,
        "target_transform": regression_config.target_transform,
        "inverse_transform": regression_config.inverse_transform,
        "prediction_quantum": config.prediction_quantum,
        "selected_hyperparameters": selected_hyperparameters,
        "scaler_mean": learned_state["scaler_mean"],
        "scaler_scale": learned_state["scaler_scale"],
        "coefficient": learned_state["coefficient"],
        "intercept": learned_state["intercept"],
        "historical_reference": reference,
        "lineage": {
            "f1_protocol_config_sha256": canonical_config_sha256(protocol),
            "f4_config_sha256": canonical_f4_config_sha256(regression_config),
            "f7_config_sha256": canonical_f7_config_sha256(config),
            "final_dataset_sha256": dataset["sha256"],
            "f5_oof_sha256": oof["sha256"],
            "f6_analysis_sha256": f6_analysis["sha256"],
            "fit_manifest_sha256": candidate.manifest["sha256"],
            "training_rows_sha256": candidate.manifest["training_rows_sha256"],
            "learned_state_sha256": candidate.manifest["learned_state_sha256"],
        },
        "training": {
            "row_count": len(training_rows),
            "feature_start": min(str(row["feature_session"]) for row in training_rows),
            "feature_end": max(str(row["feature_session"]) for row in training_rows),
            "target_end": max(str(row["target_session"]) for row in training_rows),
            "previous_outer_period_rows_included_as_historical_training": True,
            "oof_predictions_or_evaluation_metrics_used_for_fitting": False,
        },
        "research_claim_boundary": {
            "retrospective_historical_oos_evidence": True,
            "prospective_accuracy": False,
            "price_direction_forecast": False,
            "investment_advice": False,
        },
        "final_model_selected": True,
        "model_artifact_persisted": True,
        "deployed": False,
        "m7_rerun_performed": False,
    }
    artifact = {**artifact_content, "sha256": _hash(artifact_content)}
    max_difference = _verify_artifact_predictions(artifact, candidate, training_rows)
    report = {
        "report_version": config.report_version,
        "passed": True,
        "f7_config_sha256": canonical_f7_config_sha256(config),
        "artifact_sha256": artifact["sha256"],
        "selection_evidence": selection,
        "hyperparameter_selection": hyperparameter_evidence,
        "selected_model": "ridge_regression",
        "selected_hyperparameters": selected_hyperparameters,
        "training_row_count": len(training_rows),
        "training_feature_start": artifact["training"]["feature_start"],
        "training_feature_end": artifact["training"]["feature_end"],
        "training_target_end": artifact["training"]["target_end"],
        "fit_manifest_sha256": candidate.manifest["sha256"],
        "training_rows_sha256": candidate.manifest["training_rows_sha256"],
        "learned_state_sha256": candidate.manifest["learned_state_sha256"],
        "repeated_fit_learned_state_sha256": repeated.manifest["learned_state_sha256"],
        "artifact_inference_max_abs_difference": max_difference,
        "historical_reference_row_count": reference["row_count"],
        "band_cutoffs": reference["band_cutoffs"],
        "final_model_selected": True,
        "model_artifact_persisted": True,
        "prospective_accuracy_claimed": False,
        "deployed": False,
        "m7_rerun_performed": False,
        "raw_training_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return artifact, report


def verify_f7_inputs(
    config: FinalModelFreezeConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset: dict[str, object],
    oof: dict[str, object],
    f6_analysis: dict[str, object],
) -> list[dict[str, object]]:
    for payload, name in ((dataset, "F2 dataset"), (oof, "F5 OOF"), (f6_analysis, "F6 analysis")):
        _verify_hash(payload, name)
    if canonical_config_sha256(protocol) != config.f1_protocol_config_sha256:
        raise ValueError("F7/F1 lineage mismatch")
    if canonical_f4_config_sha256(regression_config) != config.f4_config_sha256:
        raise ValueError("F7/F4 lineage mismatch")
    if dataset["sha256"] != config.final_dataset_sha256:
        raise ValueError("F7/F2 lineage mismatch")
    if oof["sha256"] != config.f5_oof_sha256:
        raise ValueError("F7/F5 lineage mismatch")
    if f6_analysis["sha256"] != config.f6_analysis_sha256:
        raise ValueError("F7/F6 lineage mismatch")
    if f6_analysis.get("final_model_selected") is not False:
        raise ValueError("F6 evidence already selected a model")
    if f6_analysis.get("subgroup_results_used_for_tuning") is not False:
        raise ValueError("F6 evidence indicates subgroup tuning")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("F7 dataset rows are missing")
    return rows


def select_final_model(
    config: FinalModelFreezeConfig, f6_analysis: dict[str, object]
) -> dict[str, object]:
    summaries = f6_analysis.get("model_summaries")
    if not isinstance(summaries, dict) or set(summaries) != set(COMPLEXITY_ORDER):
        raise ValueError("F7 model summaries are incomplete")
    best_spearman = max(float(value["mean_spearman"]) for value in summaries.values())
    tie_candidates = [
        name
        for name, value in summaries.items()
        if best_spearman - float(value["mean_spearman"])
        <= config.selection_rule.practical_tie_margin_spearman
    ]
    selected = min(
        tie_candidates,
        key=lambda name: (
            float(summaries[name]["mean_mae"]),
            -float(summaries[name]["worst_spearman"]),
            COMPLEXITY_ORDER[name],
        ),
    )
    if selected != config.selection_rule.expected_selected_model:
        raise ValueError("F7 selected model differs from frozen expectation")
    return {
        "primary_metric": config.selection_rule.primary,
        "best_mean_outer_spearman": best_spearman,
        "practical_tie_margin_spearman": config.selection_rule.practical_tie_margin_spearman,
        "practical_tie_candidates": sorted(tie_candidates),
        "candidate_metrics": summaries,
        "tie_broken_by": "lower_mean_outer_mae",
        "selected_model": selected,
        "single_period_or_subgroup_selection_used": False,
    }


def select_final_hyperparameters(
    config: FinalModelFreezeConfig,
    protocol: FinalStudyProtocolConfig,
    regression_config: FinalRegressionConfig,
    dataset_sha256: str,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    model_spec = next(model for model in protocol.models if model.name == "ridge_regression")
    alphas = model_spec.hyperparameters.get("alpha")
    if not isinstance(alphas, list) or not alphas:
        raise ValueError("F7 Ridge alpha grid is missing")
    evidence = []
    for alpha in alphas:
        fold_metrics = []
        for year in config.final_hyperparameter_selection.validation_years:
            training_end = date(year - 1, 12, 31)
            validation_start = date(year, 1, 1)
            validation_end = date(year, 12, 31)
            training = [
                row
                for row in rows
                if config.final_hyperparameter_selection.training_start
                <= date.fromisoformat(str(row["feature_session"]))
                <= training_end
                and date.fromisoformat(str(row["target_session"])) < validation_start
            ]
            validation = [
                row
                for row in rows
                if validation_start
                <= date.fromisoformat(str(row["feature_session"]))
                <= validation_end
            ]
            context = TemporalFitContext(
                name=f"f7_inner_{year}",
                training_start=config.final_hyperparameter_selection.training_start,
                training_end=training_end,
                next_validation_or_evaluation_start=validation_start,
            )
            candidate = fit_candidate(
                regression_config,
                protocol,
                dataset_sha256,
                training,
                context,
                "ridge_regression",
                {"alpha": float(alpha)},
            )
            predicted = candidate.predict_rows(validation)
            actual = np.asarray(
                [float(row["target"][regression_config.target_field]) for row in validation],
                dtype=np.float64,
            )
            metrics = evaluate_predictions(actual, predicted)
            fold_metrics.append(
                {
                    "validation_year": year,
                    "training_row_count": len(training),
                    "validation_row_count": len(validation),
                    "mae": metrics["mae"],
                    "spearman": metrics["spearman"],
                }
            )
        evidence.append(
            ParameterEvidence(
                hyperparameters={"alpha": float(alpha)},
                fold_metrics=fold_metrics,
                mean_spearman=float(np.mean([item["spearman"] for item in fold_metrics])),
                mean_mae=float(np.mean([item["mae"] for item in fold_metrics])),
                worst_spearman=float(min(item["spearman"] for item in fold_metrics)),
            )
        )
    selected = select_parameter_evidence("ridge_regression", evidence)
    return {
        "method": config.final_hyperparameter_selection.method,
        "validation_years": list(config.final_hyperparameter_selection.validation_years),
        "candidate_evidence": [
            {
                "hyperparameters": item.hyperparameters,
                "fold_metrics": item.fold_metrics,
                "mean_spearman": item.mean_spearman,
                "mean_mae": item.mean_mae,
                "worst_spearman": item.worst_spearman,
            }
            for item in evidence
        ],
        "selected_hyperparameters": selected.hyperparameters,
        "outer_or_f6_subgroup_rows_used_for_selection": False,
    }


def predict_from_artifact(
    artifact: dict[str, object],
    ticker: str,
    as_of_date: str,
    information_cutoff: str,
    features: dict[str, object],
) -> dict[str, object]:
    verify_model_artifact(artifact)
    if not ticker.strip():
        raise ValueError("inference ticker is empty")
    parsed_date = date.fromisoformat(as_of_date)
    cutoff = datetime.fromisoformat(information_cutoff)
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("inference information cutoff must be timezone-aware")
    if cutoff.date() != parsed_date:
        raise ValueError("inference cutoff date differs from as_of_date")
    if set(features) != set(artifact["feature_names"]):
        raise ValueError("inference features differ from frozen contract")
    score = _predict_score(artifact, features)
    reference = [float(value) for value in artifact["historical_reference"]["sorted_predictions"]]
    percentile = round(
        100 * bisect.bisect_right(reference, score) / len(reference),
        int(artifact["historical_reference"]["percentile_output_decimals"]),
    )
    cutoffs = [float(value) for value in artifact["historical_reference"]["band_cutoffs"]]
    labels = artifact["historical_reference"]["band_labels"]
    if score < cutoffs[0]:
        band = labels[0]
    elif score < cutoffs[1]:
        band = labels[1]
    elif score < cutoffs[2]:
        band = labels[2]
    else:
        band = labels[3]
    return {
        "ticker": ticker,
        "as_of_date": parsed_date.isoformat(),
        "information_cutoff": cutoff.isoformat(),
        "predicted_volatility_surprise": _format_number(
            score, str(artifact["prediction_quantum"])
        ),
        "historical_percentile": percentile,
        "risk_band": band,
        "model_version": artifact["model_version"],
        "feature_pipeline_version": artifact["feature_pipeline_version"],
    }


def verify_model_artifact(artifact: dict[str, object]) -> None:
    _verify_hash(artifact, "F7 model artifact")
    if artifact.get("schema_version") != ARTIFACT_VERSION:
        raise ValueError("unexpected F7 model artifact version")
    if artifact.get("artifact_format") != "SAFE_JSON_NO_PICKLE":
        raise ValueError("F7 artifact format is unsafe or unsupported")
    if tuple(artifact.get("feature_names", ())) != FEATURE_NAMES:
        raise ValueError("F7 artifact feature order drifted")
    size = len(FEATURE_NAMES)
    for name in ("scaler_mean", "scaler_scale", "coefficient"):
        values = artifact.get(name)
        if not isinstance(values, list) or len(values) != size:
            raise ValueError(f"F7 artifact {name} has invalid length")
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError(f"F7 artifact {name} is non-finite")
    if any(float(value) <= 0 for value in artifact["scaler_scale"]):
        raise ValueError("F7 artifact scaler contains non-positive scale")
    reference = artifact.get("historical_reference")
    predictions = reference.get("sorted_predictions") if isinstance(reference, dict) else None
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("F7 historical reference is missing")
    numeric = [float(value) for value in predictions]
    if numeric != sorted(numeric) or not all(math.isfinite(value) for value in numeric):
        raise ValueError("F7 historical reference is invalid")
    if reference.get("row_count") != len(numeric):
        raise ValueError("F7 historical reference count mismatch")


def write_f7_outputs(
    artifact_path: Path,
    report_path: Path,
    artifact: dict[str, object],
    report: dict[str, object],
) -> None:
    write_immutable_json(artifact_path, artifact)
    write_report(report_path, report)


def _final_training_rows(
    config: FinalModelFreezeConfig, rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    selected = [
        row
        for row in rows
        if config.final_fit.training_feature_start
        <= date.fromisoformat(str(row["feature_session"]))
        <= config.final_fit.training_feature_end
        and date.fromisoformat(str(row["target_session"]))
        <= config.final_fit.training_target_end
        and date.fromisoformat(str(row["target_session"]))
        < config.final_fit.next_unseen_session_boundary
    ]
    if config.final_fit.use_all_eligible_rows and len(selected) != len(rows):
        raise ValueError("F7 final fit omitted eligible F2 rows")
    return selected


def _historical_reference(
    config: FinalModelFreezeConfig, oof: dict[str, object], model_name: str
) -> dict[str, object]:
    values = sorted(
        float(row["prediction"])
        for row in oof["rows"]
        if row["model_name"] == model_name
    )
    if len(values) != config.historical_reference.expected_row_count:
        raise ValueError("F7 selected-model OOF reference count mismatch")
    cutoffs = np.quantile(
        np.asarray(values, dtype=np.float64),
        config.historical_reference.band_quantiles,
        method=config.historical_reference.quantile_method,
    )
    return {
        "source": config.historical_reference.source,
        "source_oof_sha256": oof["sha256"],
        "row_count": len(values),
        "quantile_method": config.historical_reference.quantile_method,
        "percentile_method": config.historical_reference.percentile_method,
        "percentile_output_decimals": config.historical_reference.percentile_output_decimals,
        "band_quantiles": list(config.historical_reference.band_quantiles),
        "band_cutoffs": [
            _format_number(value, config.prediction_quantum) for value in cutoffs
        ],
        "band_labels": list(config.historical_reference.band_labels),
        "boundary_rule": config.historical_reference.boundary_rule,
        "sorted_predictions": [
            _format_number(value, config.prediction_quantum) for value in values
        ],
    }


def _predict_score(artifact: dict[str, object], features: dict[str, object]) -> float:
    matrix = np.asarray(
        [float(features[name]) for name in artifact["feature_names"]], dtype=np.float64
    )
    if not np.isfinite(matrix).all():
        raise ValueError("inference features contain non-finite values")
    mean = np.asarray(artifact["scaler_mean"], dtype=np.float64)
    scale = np.asarray(artifact["scaler_scale"], dtype=np.float64)
    coefficient = np.asarray(artifact["coefficient"], dtype=np.float64)
    transformed = (matrix - mean) / scale
    log_prediction = float(np.dot(transformed, coefficient) + float(artifact["intercept"]))
    score = max(0.0, math.expm1(log_prediction))
    return float(_format_number(score, str(artifact["prediction_quantum"])))


def _verify_artifact_predictions(
    artifact: dict[str, object], candidate: object, rows: list[dict[str, object]]
) -> float:
    verify_model_artifact(artifact)
    expected = candidate.predict_rows(rows)
    actual = np.asarray(
        [_predict_score(artifact, row["features"]) for row in rows], dtype=np.float64
    )
    difference = float(np.max(np.abs(expected - actual)))
    if difference > 1e-10:
        raise ValueError("F7 JSON artifact inference differs from fitted Ridge")
    return difference


def _format_number(value: object, quantum: str) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("F7 artifact contains non-finite number")
    return format(
        Decimal(str(number)).quantize(Decimal(quantum), rounding=ROUND_HALF_EVEN), "f"
    )


def _verify_hash(payload: dict[str, object], name: str) -> None:
    content = {key: value for key, value in payload.items() if key != "sha256"}
    if payload.get("sha256") != _hash(content):
        raise ValueError(f"{name} SHA-256 mismatch")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
