from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.planning.final_study_protocol import (
    FinalStudyProtocolConfig,
    canonical_config_sha256,
    derive_inner_folds,
    load_final_study_config,
    validate_outer_rows,
)

CONFIG_PATH = Path("research/configs/final_volatility_surprise_study.v1.json")


def _config() -> FinalStudyProtocolConfig:
    return load_final_study_config(CONFIG_PATH)


def _row(config: FinalStudyProtocolConfig, feature: str, target: str) -> dict[str, object]:
    return {
        "ticker": "2330",
        "feature_session": feature,
        "target_session": target,
        "information_cutoff": f"{feature}T13:30:00+08:00",
        "features": {name: 0.01 for name in config.features.fixed_feature_names},
        "target": 1.2,
        "source_lineage": {"market_dataset_sha256": "a" * 64},
    }


def test_f1_config_freezes_continuous_target_and_claim_boundary() -> None:
    config = _config()

    assert config.status == "F1_PROTOCOL_FROZEN_IMPLEMENTATION_NOT_RUN"
    assert config.primary_target.name == "next_session_stock_normalized_abs_log_return_v1"
    assert config.primary_target.trailing_sessions == 20
    assert config.primary_target.ddof == 0
    assert config.primary_target.minimum_denominator_exclusive == 1e-8
    assert config.training_authorized_by_f1 is False
    assert config.f2_started is False
    assert len(canonical_config_sha256(config)) == 64


def test_outer_folds_are_chronological_and_use_observed_coverage() -> None:
    config = _config()
    folds = config.outer_evaluation.folds

    assert len(folds) == 7
    assert folds[0].evaluation_start.isoformat() == "2017-01-01"
    assert folds[-1].evaluation_end.isoformat() == "2026-08-26"
    assert config.historical_market_dataset.observed_start.isoformat() == "2010-01-04"
    assert config.historical_market_dataset.observed_end.isoformat() == "2026-08-26"
    assert config.historical_market_dataset.claim_as_new_sealed_test is False


def test_inner_folds_stay_strictly_inside_each_outer_training_history() -> None:
    config = _config()
    for outer in config.outer_evaluation.folds:
        inner = derive_inner_folds(config, outer)
        assert len(inner) == 3
        assert all(item.train_end < item.validation_start for item in inner)
        assert all(item.validation_end <= outer.train_end for item in inner)
        assert all(item.validation_end < outer.evaluation_start for item in inner)


def test_random_split_and_outer_validation_tuning_are_schema_forbidden() -> None:
    payload = __import__("json").loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["outer_evaluation"]["random_split_allowed"] = True
    with pytest.raises(ValidationError):
        FinalStudyProtocolConfig.model_validate(payload)

    payload = __import__("json").loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["inner_validation"]["outer_validation_rows_allowed"] = True
    with pytest.raises(ValidationError):
        FinalStudyProtocolConfig.model_validate(payload)


def test_row_guard_rejects_target_overlap_future_features_and_duplicates() -> None:
    config = _config()
    fold = config.outer_evaluation.folds[0]
    train = [_row(config, "2016-12-28", "2016-12-29")]
    evaluation = [_row(config, "2017-01-03", "2017-01-04")]
    validate_outer_rows(config, fold, train, evaluation)

    overlapping = [_row(config, "2016-12-30", "2017-01-03")]
    with pytest.raises(ValueError, match="overlaps outer evaluation"):
        validate_outer_rows(config, fold, overlapping, evaluation)

    future = deepcopy(evaluation)
    future[0]["features"]["next_abs_log_return"] = 0.5
    with pytest.raises(ValueError, match="future/target field"):
        validate_outer_rows(config, fold, train, future)

    duplicate = [_row(config, "2016-12-28", "2016-12-29")]
    with pytest.raises(ValueError, match="duplicate or cross-fold"):
        validate_outer_rows(config, fold, train, duplicate)


def test_model_set_is_compact_regression_only_and_xgboost_is_excluded() -> None:
    config = _config()

    assert [model.name for model in config.models] == [
        "normalized_move_persistence",
        "ridge_regression",
        "hist_gradient_boosting_regressor",
    ]
    assert config.xgboost_status == "EXCLUDED_FROM_F1_MODEL_SET_DEPENDENCY_NOT_JUSTIFIED"
    assert config.neural_time_series_models_allowed is False


def test_historical_binary_hashes_are_preserved_in_frozen_config() -> None:
    payload = __import__("json").loads(CONFIG_PATH.read_text(encoding="utf-8"))
    history = payload["exploratory_binary_history"]

    assert history["m7_evaluation_sha256"] == (
        "4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe"
    )
    assert history["m8_analysis_sha256"] == (
        "c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b"
    )
    assert history["m9_analysis_sha256"] == (
        "5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2"
    )
    assert history["m10_analysis_sha256"] == (
        "21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c"
    )
    assert history["m11_analysis_sha256"] == (
        "76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88"
    )
    assert history["may_be_deleted_or_rewritten"] is False


def test_f1_does_not_relabel_history_as_prospective_or_pristine() -> None:
    payload = CONFIG_PATH.read_text(encoding="utf-8")

    assert '"claim_as_new_sealed_test": false' in payload
    assert '"prospective validation"' in payload
    assert '"pristine untouched final test"' in payload
    assert '"training_authorized_by_f1": false' in payload

