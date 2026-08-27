from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pipelines.features.final_study_builder import write_immutable_json, write_report
from research.modeling.final_regressors import MODEL_NAMES
from research.modeling.final_temporal_evaluation import (
    FinalTemporalEvaluationConfig,
    canonical_f5_config_sha256,
    evaluate_predictions,
)
from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    OuterFold,
    canonical_config_sha256,
)

CONFIG_VERSION = "final-ranking-robustness-config-v1"
ANALYSIS_VERSION = "final-ranking-robustness-analysis-v1"
REPORT_VERSION = "f6-final-ranking-robustness-report-v1"
REGIME_LABELS = ("LOW", "MIDDLE", "HIGH")


class BootstrapConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: Literal[True]
    cluster: Literal["feature_session"]
    stratify_by: Literal["outer_fold"]
    replicates: int = Field(ge=10, le=10_000)
    confidence_level: float = Field(gt=0.5, lt=1.0)
    random_state: int
    metrics: tuple[
        Literal[
            "mean_outer_mae",
            "mean_outer_rmse",
            "mean_outer_spearman",
            "mean_outer_top_decile_lift_ratio",
        ],
        ...,
    ]
    decile_realized_mean_intervals: Literal[True]


class FinalRankingRobustnessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["final-ranking-robustness-config-v1"] = CONFIG_VERSION
    analysis_version: Literal["final-ranking-robustness-analysis-v1"] = ANALYSIS_VERSION
    report_version: Literal["f6-final-ranking-robustness-report-v1"] = REPORT_VERSION
    f1_protocol_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f5_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f5_oof_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    models: tuple[str, ...]
    outer_fold_names: tuple[str, ...]
    metrics: tuple[Literal["mae", "rmse", "spearman", "top_decile_lift_ratio"], ...]
    top_decile_fraction: float
    top_quintile_fraction: float
    lift_definition: Literal[
        "mean_realized_primary_target_in_predicted_top_fraction_divided_by_mean_realized_primary_target_in_group"
    ]
    lift_zero_denominator_policy: Literal["UNDEFINED_AND_REPORT"]
    decile_count: Literal[10]
    decile_labels_low_to_high: tuple[str, ...]
    decile_assignment_scope: Literal["WITHIN_MODEL_AND_OUTER_FOLD"]
    decile_tie_break_order: tuple[str, ...]
    stock_regime_feature: Literal["volatility_log_return_20"]
    market_regime_feature: Literal["benchmark_volatility_log_return_20"]
    regime_quantiles: tuple[float, float]
    regime_labels: tuple[str, ...]
    regime_boundary_rule: Literal["LOW_LE_LOWER_MIDDLE_LE_UPPER_HIGH_GT_UPPER"]
    regime_fit_scope: Literal["CURRENT_OUTER_TRAINING_HISTORY_ONLY"]
    minimum_subgroup_rows: int = Field(ge=1)
    bootstrap: BootstrapConfig
    subgroup_results_used_for_tuning: Literal[False]
    final_model_selection_performed_in_f6: Literal[False]
    model_artifact_persisted_in_f6: Literal[False]
    m7_rerun_allowed: Literal[False]
    raw_rows_committed: Literal[False]

    @field_validator("top_decile_fraction", "top_quintile_fraction")
    @classmethod
    def valid_fraction(cls, value: float) -> float:
        if not 0 < value < 1:
            raise ValueError("ranking fraction must be inside (0, 1)")
        return value

    @model_validator(mode="after")
    def frozen_contract(self) -> FinalRankingRobustnessConfig:
        if self.models != MODEL_NAMES:
            raise ValueError("F6 model set/order drifted")
        if self.metrics != ("mae", "rmse", "spearman", "top_decile_lift_ratio"):
            raise ValueError("F6 robustness metrics drifted")
        if self.top_decile_fraction != 0.1 or self.top_quintile_fraction != 0.2:
            raise ValueError("F6 lift fractions drifted")
        expected_deciles = tuple(f"D{value}" for value in range(1, 11))
        if self.decile_labels_low_to_high != expected_deciles:
            raise ValueError("F6 decile labels drifted")
        if self.decile_tie_break_order != (
            "predicted_score_desc",
            "feature_session_asc",
            "ticker_asc",
        ):
            raise ValueError("F6 decile tie-break drifted")
        if self.regime_labels != REGIME_LABELS:
            raise ValueError("F6 regime labels drifted")
        if not 0 < self.regime_quantiles[0] < self.regime_quantiles[1] < 1:
            raise ValueError("F6 regime quantiles must be ordered")
        return self


def load_final_ranking_robustness_config(path: Path) -> FinalRankingRobustnessConfig:
    return FinalRankingRobustnessConfig.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_f6_config_sha256(config: FinalRankingRobustnessConfig) -> str:
    return _hash(config.model_dump(mode="json"))


def analyze_final_ranking_robustness(
    config: FinalRankingRobustnessConfig,
    protocol: FinalStudyProtocolConfig,
    f5_config: FinalTemporalEvaluationConfig,
    dataset: dict[str, object],
    oof: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    dataset_rows, oof_rows = verify_f6_inputs(config, protocol, f5_config, dataset, oof)
    fold_map = {fold.name: fold for fold in protocol.outer_evaluation.folds}
    thresholds = fit_outer_regime_thresholds(config, dataset_rows, fold_map)
    enriched = enrich_oof_rows(config, dataset_rows, oof_rows, thresholds)
    assign_fold_deciles(enriched, config.decile_count)

    fold_metrics = _fold_metrics(enriched, config)
    model_summaries = _model_summaries(fold_metrics)
    deciles = _decile_summaries(enriched, config)
    robustness = {
        "outer_fold": _grouped_robustness(enriched, "outer_fold", config),
        "ticker": _grouped_robustness(enriched, "ticker", config),
        "historical_stock_volatility_regime": _grouped_robustness(
            enriched, "stock_regime", config
        ),
        "historical_market_volatility_regime": _grouped_robustness(
            enriched, "market_regime", config
        ),
        "predicted_score_decile": deciles,
    }
    uncertainty = cluster_bootstrap(enriched, config)
    _attach_decile_intervals(deciles, uncertainty)
    config_sha256 = canonical_f6_config_sha256(config)
    content = {
        "schema_version": config.analysis_version,
        "config_sha256": config_sha256,
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "final_dataset_sha256": dataset["sha256"],
        "f5_config_sha256": canonical_f5_config_sha256(f5_config),
        "f5_oof_sha256": oof["sha256"],
        "models": list(config.models),
        "outer_folds": list(config.outer_fold_names),
        "unique_evaluation_row_count": len(enriched) // len(config.models),
        "oof_prediction_row_count": len(enriched),
        "regime_thresholds": thresholds,
        "fold_metrics": fold_metrics,
        "model_summaries": model_summaries,
        "decile_analysis": deciles,
        "robustness": robustness,
        "cluster_bootstrap": uncertainty,
        "subgroup_results_used_for_tuning": False,
        "final_model_selected": False,
        "model_artifact_persisted": False,
        "m7_rerun_performed": False,
        "rows_persisted": False,
    }
    analysis = {**content, "sha256": _hash(content)}
    report = {
        "report_version": config.report_version,
        "passed": True,
        "analysis_sha256": analysis["sha256"],
        **{key: value for key, value in content.items() if key != "schema_version"},
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return analysis, report


def verify_f6_inputs(
    config: FinalRankingRobustnessConfig,
    protocol: FinalStudyProtocolConfig,
    f5_config: FinalTemporalEvaluationConfig,
    dataset: dict[str, object],
    oof: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    _verify_hash(dataset, "F2 dataset")
    _verify_hash(oof, "F5 OOF")
    if canonical_config_sha256(protocol) != config.f1_protocol_config_sha256:
        raise ValueError("F6/F1 protocol lineage mismatch")
    if canonical_f5_config_sha256(f5_config) != config.f5_config_sha256:
        raise ValueError("F6/F5 config lineage mismatch")
    if dataset["sha256"] != config.final_dataset_sha256:
        raise ValueError("F6/F2 dataset lineage mismatch")
    if oof["sha256"] != config.f5_oof_sha256:
        raise ValueError("F6/F5 OOF lineage mismatch")
    if tuple(oof.get("models", ())) != config.models:
        raise ValueError("F6/F5 model set mismatch")
    if tuple(oof.get("outer_folds", ())) != config.outer_fold_names:
        raise ValueError("F6/F5 outer folds mismatch")
    if tuple(fold.name for fold in protocol.outer_evaluation.folds) != config.outer_fold_names:
        raise ValueError("F6 outer folds differ from F1")
    if oof.get("final_model_selected") is not False:
        raise ValueError("F6 requires unselected F5 predictions")
    if oof.get("f6_analysis_performed") is not False:
        raise ValueError("F5 OOF incorrectly claims F6 was performed")
    dataset_rows = dataset.get("rows")
    oof_rows = oof.get("rows")
    if not isinstance(dataset_rows, list) or not dataset_rows:
        raise ValueError("F2 dataset rows are missing")
    if not isinstance(oof_rows, list) or not oof_rows:
        raise ValueError("F5 OOF rows are missing")
    return dataset_rows, oof_rows


def fit_outer_regime_thresholds(
    config: FinalRankingRobustnessConfig,
    dataset_rows: list[dict[str, object]],
    fold_map: dict[str, OuterFold],
) -> dict[str, object]:
    output: dict[str, object] = {}
    for fold_name in config.outer_fold_names:
        fold = fold_map[fold_name]
        training = [
            row
            for row in dataset_rows
            if fold.train_start
            <= date.fromisoformat(str(row["feature_session"]))
            <= fold.train_end
            and date.fromisoformat(str(row["target_session"])) < fold.evaluation_start
        ]
        if not training:
            raise ValueError(f"F6 regime training rows are missing: {fold_name}")
        features = {}
        for label, feature in (
            ("stock_volatility", config.stock_regime_feature),
            ("market_volatility", config.market_regime_feature),
        ):
            values = np.asarray(
                [float(row["features"][feature]) for row in training], dtype=np.float64
            )
            if not np.isfinite(values).all():
                raise ValueError(f"non-finite F6 regime feature: {fold_name}.{feature}")
            cutoffs = np.quantile(values, config.regime_quantiles, method="linear")
            features[label] = {
                "feature": feature,
                "lower_tertile": float(cutoffs[0]),
                "upper_tertile": float(cutoffs[1]),
            }
        output[fold_name] = {
            "fit_scope": config.regime_fit_scope,
            "training_start": fold.train_start.isoformat(),
            "training_end": fold.train_end.isoformat(),
            "evaluation_start": fold.evaluation_start.isoformat(),
            "training_row_count": len(training),
            "training_targets_precede_evaluation": max(
                str(row["target_session"]) for row in training
            )
            < fold.evaluation_start.isoformat(),
            **features,
        }
    return output


def enrich_oof_rows(
    config: FinalRankingRobustnessConfig,
    dataset_rows: list[dict[str, object]],
    oof_rows: list[dict[str, object]],
    thresholds: dict[str, object],
) -> list[dict[str, object]]:
    source = {}
    for row in dataset_rows:
        identity = (str(row["ticker"]), str(row["feature_session"]))
        if identity in source:
            raise ValueError("duplicate F2 ticker/session identity")
        source[identity] = row
    seen = set()
    output = []
    for row in oof_rows:
        identity = (
            str(row["model_name"]),
            str(row["outer_fold"]),
            str(row["ticker"]),
            str(row["feature_session"]),
        )
        if identity in seen:
            raise ValueError("duplicate F5 model/fold/ticker/session identity")
        seen.add(identity)
        dataset_row = source.get((identity[2], identity[3]))
        if dataset_row is None:
            raise ValueError("F5 OOF identity is absent from F2")
        if row.get("source_row_sha256") != dataset_row.get("row_sha256"):
            raise ValueError("F5 OOF source row lineage mismatch")
        actual = float(row["realized_target"])
        expected = float(dataset_row["target"]["primary"])
        prediction = float(row["prediction"])
        if not math.isfinite(actual) or not math.isfinite(prediction) or prediction < 0:
            raise ValueError("F6 received invalid prediction/target")
        if actual != expected:
            raise ValueError("F5 OOF realized target differs from F2")
        fold_thresholds = thresholds[identity[1]]
        output.append(
            {
                "model_name": identity[0],
                "outer_fold": identity[1],
                "ticker": identity[2],
                "feature_session": identity[3],
                "prediction": prediction,
                "realized_target": actual,
                "stock_regime": _regime(
                    float(dataset_row["features"][config.stock_regime_feature]),
                    fold_thresholds["stock_volatility"],
                ),
                "market_regime": _regime(
                    float(dataset_row["features"][config.market_regime_feature]),
                    fold_thresholds["market_volatility"],
                ),
            }
        )
    expected_count = len(config.models) * len(
        {(row["ticker"], row["feature_session"]) for row in output}
    )
    if len(output) != expected_count:
        raise ValueError("F6 OOF model coverage is incomplete")
    return sorted(
        output,
        key=lambda row: (
            str(row["model_name"]),
            str(row["outer_fold"]),
            str(row["feature_session"]),
            str(row["ticker"]),
        ),
    )


def assign_fold_deciles(rows: list[dict[str, object]], decile_count: int) -> None:
    groups: defaultdict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["model_name"]), str(row["outer_fold"]))].append(row)
    for group in groups.values():
        ordered = _ranked(group)
        size = len(ordered)
        for position, row in enumerate(ordered):
            top_bucket = min(decile_count - 1, position * decile_count // size)
            row["predicted_decile"] = f"D{decile_count - top_bucket}"


def lift_ratio(rows: list[dict[str, object]], fraction: float) -> float | None:
    if not rows:
        return None
    denominator = float(np.mean([float(row["realized_target"]) for row in rows]))
    if not math.isfinite(denominator) or denominator == 0:
        return None
    count = math.ceil(fraction * len(rows))
    top = _ranked(rows)[:count]
    numerator = float(np.mean([float(row["realized_target"]) for row in top]))
    return numerator / denominator


def cluster_bootstrap(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    grouped: defaultdict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[
            (str(row["model_name"]), str(row["outer_fold"]), str(row["feature_session"]))
        ].append(row)
    sessions_by_fold: dict[str, tuple[str, ...]] = {}
    for fold in config.outer_fold_names:
        reference = tuple(
            sorted(
                session
                for model, current_fold, session in grouped
                if model == config.models[0] and current_fold == fold
            )
        )
        if not reference:
            raise ValueError(f"F6 bootstrap cluster is empty: {fold}")
        for model in config.models[1:]:
            candidate = tuple(
                sorted(
                    session
                    for current_model, current_fold, session in grouped
                    if current_model == model and current_fold == fold
                )
            )
            if candidate != reference:
                raise ValueError("F6 bootstrap session coverage differs by model")
        sessions_by_fold[fold] = reference

    rng = np.random.default_rng(config.bootstrap.random_state)
    samples: dict[str, defaultdict[str, list[float]]] = {
        model: defaultdict(list) for model in config.models
    }
    decile_samples: dict[str, defaultdict[str, list[float]]] = {
        model: defaultdict(list) for model in config.models
    }
    for _ in range(config.bootstrap.replicates):
        selected_by_fold = {
            fold: rng.choice(sessions, size=len(sessions), replace=True)
            for fold, sessions in sessions_by_fold.items()
        }
        for model in config.models:
            fold_values: defaultdict[str, list[float]] = defaultdict(list)
            sampled_all = []
            for fold in config.outer_fold_names:
                sampled = [
                    row
                    for session in selected_by_fold[fold]
                    for row in grouped[(model, fold, str(session))]
                ]
                sampled_all.extend(sampled)
                metrics = _metrics(sampled, config)
                fold_values["mean_outer_mae"].append(float(metrics["mae"]))
                fold_values["mean_outer_rmse"].append(float(metrics["rmse"]))
                fold_values["mean_outer_spearman"].append(float(metrics["spearman"]))
                lift = metrics["top_decile_lift_ratio"]
                if lift is not None:
                    fold_values["mean_outer_top_decile_lift_ratio"].append(float(lift))
            for metric in config.bootstrap.metrics:
                values = fold_values[metric]
                if len(values) == len(config.outer_fold_names):
                    samples[model][metric].append(float(np.mean(values)))
            for label in config.decile_labels_low_to_high:
                values = [
                    float(row["realized_target"])
                    for row in sampled_all
                    if row["predicted_decile"] == label
                ]
                if values:
                    decile_samples[model][label].append(float(np.mean(values)))

    alpha = (1 - config.bootstrap.confidence_level) / 2
    return {
        "method": "outer_fold_stratified_feature_session_cluster_bootstrap",
        "replicates_requested": config.bootstrap.replicates,
        "confidence_level": config.bootstrap.confidence_level,
        "random_state": config.bootstrap.random_state,
        "cluster_counts_by_fold": {
            fold: len(sessions) for fold, sessions in sessions_by_fold.items()
        },
        "models": {
            model: {
                "metric_intervals": {
                    metric: _interval(values, alpha)
                    for metric, values in sorted(samples[model].items())
                },
                "decile_realized_mean_intervals": {
                    label: _interval(decile_samples[model][label], alpha)
                    for label in config.decile_labels_low_to_high
                },
            }
            for model in config.models
        },
    }


def _fold_metrics(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    output = {}
    for model in config.models:
        output[model] = {}
        for fold in config.outer_fold_names:
            group = [
                row
                for row in rows
                if row["model_name"] == model and row["outer_fold"] == fold
            ]
            output[model][fold] = {
                **_metrics(group, config),
                "top_quintile_lift_ratio": lift_ratio(group, config.top_quintile_fraction),
            }
    return output


def _model_summaries(fold_metrics: dict[str, object]) -> dict[str, object]:
    output = {}
    for model, by_fold in fold_metrics.items():
        values = list(by_fold.values())
        output[model] = {
            "fold_count": len(values),
            "mean_mae": float(np.mean([value["mae"] for value in values])),
            "median_mae": float(median(value["mae"] for value in values)),
            "mean_rmse": float(np.mean([value["rmse"] for value in values])),
            "mean_spearman": float(np.mean([value["spearman"] for value in values])),
            "median_spearman": float(median(value["spearman"] for value in values)),
            "worst_spearman": float(min(value["spearman"] for value in values)),
            "mean_top_decile_lift_ratio": _optional_mean(
                [value["top_decile_lift_ratio"] for value in values]
            ),
            "mean_top_quintile_lift_ratio": _optional_mean(
                [value["top_quintile_lift_ratio"] for value in values]
            ),
        }
    return output


def _decile_summaries(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    output = {}
    for model in config.models:
        model_rows = [row for row in rows if row["model_name"] == model]
        output[model] = {
            "pooled_outer_assigned_deciles": _decile_sequence_summary(model_rows, config),
            "by_outer_fold": {
                fold: _decile_sequence_summary(
                    [row for row in model_rows if row["outer_fold"] == fold], config
                )
                for fold in config.outer_fold_names
            },
        }
    return output


def _decile_sequence_summary(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    buckets = {}
    realized_means = []
    for label in config.decile_labels_low_to_high:
        group = [row for row in rows if row["predicted_decile"] == label]
        if not group:
            raise ValueError(f"F6 predicted decile is empty: {label}")
        realized = np.asarray(
            [float(row["realized_target"]) for row in group], dtype=np.float64
        )
        predictions = np.asarray(
            [float(row["prediction"]) for row in group], dtype=np.float64
        )
        realized_mean = float(np.mean(realized))
        realized_means.append(realized_mean)
        buckets[label] = {
            "row_count": len(group),
            "mean_prediction": float(np.mean(predictions)),
            "mean_realized_target": realized_mean,
            "median_realized_target": float(np.median(realized)),
            "realized_target_std": float(np.std(realized, ddof=1)),
            "bootstrap_95_interval_mean_realized_target": None,
        }
    increases = sum(
        next_value >= current
        for current, next_value in zip(realized_means, realized_means[1:], strict=False)
    )
    return {
        "buckets": buckets,
        "adjacent_non_decreasing_steps": increases,
        "adjacent_step_count": len(realized_means) - 1,
        "perfect_monotonicity_required": False,
    }


def _grouped_robustness(
    rows: list[dict[str, object]], key: str, config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    output = {}
    for model in config.models:
        groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            if row["model_name"] == model:
                groups[str(row[key])].append(row)
        output[model] = {
            name: _subgroup_metrics(group, config)
            for name, group in sorted(groups.items())
        }
    return output


def _subgroup_metrics(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    if len(rows) < config.minimum_subgroup_rows:
        return {"status": "INSUFFICIENT", "row_count": len(rows), "metrics": None}
    return {"status": "OK", "row_count": len(rows), "metrics": _metrics(rows, config)}


def _metrics(
    rows: list[dict[str, object]], config: FinalRankingRobustnessConfig
) -> dict[str, object]:
    actual = np.asarray([float(row["realized_target"]) for row in rows], dtype=np.float64)
    prediction = np.asarray([float(row["prediction"]) for row in rows], dtype=np.float64)
    base = evaluate_predictions(actual, prediction)
    return {
        "row_count": len(rows),
        "mae": base["mae"],
        "rmse": base["rmse"],
        "spearman": base["spearman"],
        "constant_prediction_spearman_zeroed": base[
            "constant_prediction_spearman_zeroed"
        ],
        "top_decile_lift_ratio": lift_ratio(rows, config.top_decile_fraction),
    }


def _attach_decile_intervals(
    deciles: dict[str, object], uncertainty: dict[str, object]
) -> None:
    for model, model_output in deciles.items():
        intervals = uncertainty["models"][model]["decile_realized_mean_intervals"]
        pooled = model_output["pooled_outer_assigned_deciles"]
        for label, bucket in pooled["buckets"].items():
            bucket["bootstrap_95_interval_mean_realized_target"] = intervals[label]


def _regime(value: float, thresholds: dict[str, object]) -> str:
    if value <= float(thresholds["lower_tertile"]):
        return "LOW"
    if value <= float(thresholds["upper_tertile"]):
        return "MIDDLE"
    return "HIGH"


def _ranked(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            -float(row["prediction"]),
            str(row["feature_session"]),
            str(row["ticker"]),
        ),
    )


def _interval(values: list[float], alpha: float) -> dict[str, object]:
    if not values:
        return {"valid_replicates": 0, "lower": None, "upper": None}
    return {
        "valid_replicates": len(values),
        "lower": float(np.quantile(values, alpha)),
        "upper": float(np.quantile(values, 1 - alpha)),
    }


def _optional_mean(values: list[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return float(np.mean(present)) if present else None


def _verify_hash(payload: dict[str, object], name: str) -> None:
    content = {key: value for key, value in payload.items() if key != "sha256"}
    if payload.get("sha256") != _hash(content):
        raise ValueError(f"{name} SHA-256 mismatch")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def write_f6_outputs(
    analysis_path: Path,
    report_path: Path,
    analysis: dict[str, object],
    report: dict[str, object],
) -> None:
    write_immutable_json(analysis_path, analysis)
    write_report(report_path, report)
