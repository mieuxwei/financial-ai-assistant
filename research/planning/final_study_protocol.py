from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONFIG_VERSION = "final-volatility-surprise-study-config-v1"
PROTOCOL_VERSION = "stock-normalized-volatility-surprise-final-v1"


class HistoricalMarketDataset(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["risk-market-dataset-v1"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_start: date
    observed_end: date
    stock_row_count: int = Field(gt=0)
    benchmark_row_count: int = Field(gt=0)
    ticker_count: int = Field(gt=0)
    use_previously_inspected_periods_as_historical_outer_folds: Literal[True]
    claim_as_new_sealed_test: Literal[False]


class DatasetContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    dataset_version: Literal["final-volatility-surprise-dataset-v1"]
    required_row_fields: tuple[str, ...]
    identity_fields: tuple[Literal["ticker", "feature_session"], ...]
    random_split_allowed: Literal[False]
    target_must_be_next_observed_exchange_session: Literal[True]
    duplicate_identity_allowed: Literal[False]
    raw_provider_rows_committed: Literal[False]


class PrimaryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["next_session_stock_normalized_abs_log_return_v1"]
    formula: str
    numerator: Literal["next_session_absolute_adjusted_close_log_return"]
    denominator: Literal[
        "population_standard_deviation_of_20_adjusted_close_log_returns_ending_at_t"
    ]
    trailing_sessions: Literal[20]
    ddof: Literal[0]
    denominator_available_at: Literal["post_close_t"]
    minimum_denominator_exclusive: float = Field(gt=0, le=1e-6)
    near_zero_policy: Literal["EXCLUDE_ROW_AND_REPORT_COUNT"]
    non_finite_policy: Literal["EXCLUDE_ROW_AND_REPORT_COUNT"]
    output_quantum: Literal["0.000000000001"]
    modeling_transform: Literal["log1p"]
    inverse_transform: Literal["maximum_zero_expm1"]
    future_values_on_predictor_side_allowed: Literal[False]


class FeatureContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    pipeline_foundation: Literal["risk-features-v1"]
    fixed_feature_names: tuple[str, ...] = Field(min_length=1)
    feature_selection: Literal["NONE_FIXED_COMPACT_SET"]
    nlp_in_core_features: Literal[False]
    forbidden_feature_names: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def forbid_target_features(self) -> FeatureContract:
        overlap = set(self.fixed_feature_names) & set(self.forbidden_feature_names)
        if overlap:
            raise ValueError(f"target/future fields entered features: {sorted(overlap)}")
        return self


class OuterFold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    train_start: date
    train_end: date
    evaluation_start: date
    evaluation_end: date

    @model_validator(mode="after")
    def chronological(self) -> OuterFold:
        if self.train_start > self.train_end:
            raise ValueError("outer training dates are reversed")
        if self.train_end >= self.evaluation_start:
            raise ValueError("outer training must end before evaluation starts")
        if self.evaluation_start > self.evaluation_end:
            raise ValueError("outer evaluation dates are reversed")
        return self


class OuterEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["expanding_window_rolling_origin"]
    random_split_allowed: Literal[False]
    purge_incomplete_or_overlapping_target: Literal[True]
    folds: tuple[OuterFold, ...] = Field(min_length=3)

    @model_validator(mode="after")
    def ordered_folds(self) -> OuterEvaluation:
        names = [fold.name for fold in self.folds]
        if len(names) != len(set(names)):
            raise ValueError("outer fold names must be unique")
        for previous, current in zip(self.folds, self.folds[1:], strict=False):
            if previous.evaluation_end >= current.evaluation_start:
                raise ValueError("outer evaluation periods overlap or are unordered")
            if previous.train_end >= current.train_end:
                raise ValueError("outer training history must expand")
        return self


class InnerValidation(BaseModel):
    model_config = ConfigDict(extra="allow")

    method: Literal["latest_three_complete_calendar_years_expanding_window"]
    validation_block_years: Literal[1]
    validation_block_count: Literal[3]
    minimum_initial_training_years: int = Field(ge=3)
    must_be_contained_inside_outer_training: Literal[True]
    outer_validation_rows_allowed: Literal[False]
    selection_primary: Literal["mean_inner_spearman"]
    selection_secondary: Literal["mean_inner_mae"]


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal[
        "normalized_move_persistence",
        "ridge_regression",
        "hist_gradient_boosting_regressor",
    ]
    role: str
    implementation: str
    hyperparameters: dict[str, object]


class FinalStudyProtocolConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["final-volatility-surprise-study-config-v1"] = CONFIG_VERSION
    protocol_version: Literal["stock-normalized-volatility-surprise-final-v1"] = (
        PROTOCOL_VERSION
    )
    milestone: Literal["F1"]
    status: Literal["F1_PROTOCOL_FROZEN_IMPLEMENTATION_NOT_RUN"]
    research_framing: Literal[
        "RETROSPECTIVE_LEAKAGE_AWARE_HYPOTHESIS_INFORMED_FINAL_STUDY"
    ]
    historical_market_dataset: HistoricalMarketDataset
    dataset_contract: DatasetContract
    primary_target: PrimaryTarget
    features: FeatureContract
    outer_evaluation: OuterEvaluation
    inner_validation: InnerValidation
    models: tuple[ModelSpec, ...] = Field(min_length=3, max_length=3)
    xgboost_status: Literal["EXCLUDED_FROM_F1_MODEL_SET_DEPENDENCY_NOT_JUSTIFIED"]
    neural_time_series_models_allowed: Literal[False]
    training_authorized_by_f1: Literal[False]
    f2_started: Literal[False]

    @model_validator(mode="after")
    def frozen_model_set(self) -> FinalStudyProtocolConfig:
        names = tuple(model.name for model in self.models)
        expected = (
            "normalized_move_persistence",
            "ridge_regression",
            "hist_gradient_boosting_regressor",
        )
        if names != expected:
            raise ValueError("F1 model set or order drifted")
        return self


class DerivedInnerFold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date


def load_final_study_config(path: Path) -> FinalStudyProtocolConfig:
    return FinalStudyProtocolConfig.model_validate_json(path.read_text(encoding="utf-8"))


def derive_inner_folds(
    config: FinalStudyProtocolConfig, outer_fold: OuterFold
) -> tuple[DerivedInnerFold, ...]:
    """Derive the frozen three latest one-year inner validations inside outer training."""
    count = config.inner_validation.validation_block_count
    last_year = outer_fold.train_end.year
    first_validation_year = last_year - count + 1
    minimum_first_year = (
        outer_fold.train_start.year
        + config.inner_validation.minimum_initial_training_years
    )
    if first_validation_year < minimum_first_year:
        raise ValueError("outer fold lacks minimum history for the frozen inner design")
    folds = []
    for year in range(first_validation_year, last_year + 1):
        fold = DerivedInnerFold(
            name=f"{outer_fold.name}_inner_{year}",
            train_start=outer_fold.train_start,
            train_end=date(year - 1, 12, 31),
            validation_start=date(year, 1, 1),
            validation_end=date(year, 12, 31),
        )
        if fold.validation_end > outer_fold.train_end:
            raise ValueError("inner validation escapes outer training history")
        folds.append(fold)
    return tuple(folds)


def validate_outer_rows(
    config: FinalStudyProtocolConfig,
    fold: OuterFold,
    training_rows: list[dict[str, object]],
    evaluation_rows: list[dict[str, object]],
) -> None:
    """Validate temporal isolation and predictor-side safety without fitting a model."""
    if not training_rows or not evaluation_rows:
        raise ValueError("outer fold requires non-empty training and evaluation rows")
    seen: set[tuple[str, str]] = set()
    for role, rows in (("training", training_rows), ("evaluation", evaluation_rows)):
        for row in rows:
            identity = (str(row["ticker"]), str(row["feature_session"]))
            if identity in seen:
                raise ValueError("duplicate or cross-fold ticker/date identity")
            seen.add(identity)
            feature_session = date.fromisoformat(str(row["feature_session"]))
            target_session = date.fromisoformat(str(row["target_session"]))
            cutoff = datetime.fromisoformat(str(row["information_cutoff"]))
            if cutoff.tzinfo is None or cutoff.date() != feature_session:
                raise ValueError("information cutoff is not timezone-aware on feature session")
            if target_session <= feature_session:
                raise ValueError("target session must follow feature session")
            features = row.get("features")
            if not isinstance(features, dict):
                raise ValueError("features must be an object")
            forbidden = set(config.features.forbidden_feature_names) & set(features)
            if forbidden:
                raise ValueError(f"future/target field entered predictors: {sorted(forbidden)}")
            if set(features) != set(config.features.fixed_feature_names):
                raise ValueError("row does not match frozen F1 feature contract")
            if role == "training":
                if not fold.train_start <= feature_session <= fold.train_end:
                    raise ValueError("training feature session is outside outer training")
                if target_session >= fold.evaluation_start:
                    raise ValueError("training target overlaps outer evaluation")
            elif not fold.evaluation_start <= feature_session <= fold.evaluation_end:
                raise ValueError("evaluation feature session is outside outer evaluation")


def canonical_config_sha256(config: FinalStudyProtocolConfig) -> str:
    payload = config.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
