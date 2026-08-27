from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from research.modeling.final_regressors import (
    canonical_f4_config_sha256,
    load_final_regression_config,
)
from research.modeling.final_temporal_evaluation import (
    MODEL_NAMES,
    ParameterEvidence,
    _training_rows,
    evaluate_predictions,
    load_final_temporal_evaluation_config,
    select_parameter_evidence,
    verify_oof_rows,
)
from research.planning.final_study_protocol import (
    canonical_config_sha256,
    load_final_study_config,
)

F1_CONFIG = Path("research/configs/final_volatility_surprise_study.v1.json")
F4_CONFIG = Path("research/configs/final_regression_models.v1.json")
F5_CONFIG = Path("research/configs/final_nested_temporal_evaluation.v1.json")


def test_f5_config_matches_frozen_f1_f4_dataset_and_all_outer_folds() -> None:
    protocol = load_final_study_config(F1_CONFIG)
    regression = load_final_regression_config(F4_CONFIG)
    config = load_final_temporal_evaluation_config(F5_CONFIG)

    assert config.f1_protocol_config_sha256 == canonical_config_sha256(protocol)
    assert config.f4_config_sha256 == canonical_f4_config_sha256(regression)
    assert config.final_dataset_sha256 == (
        "2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c"
    )
    assert config.outer_fold_names == tuple(
        fold.name for fold in protocol.outer_evaluation.folds
    )
    assert config.final_model_selection_performed_in_f5 is False
    assert config.f6_analysis_performed_in_f5 is False


def test_regression_metrics_and_constant_spearman_policy_are_deterministic() -> None:
    actual = np.asarray([1.0, 2.0, 3.0, 4.0])
    perfect = evaluate_predictions(actual, actual)
    constant = evaluate_predictions(actual, np.ones(4))

    assert perfect["mae"] == 0
    assert perfect["rmse"] == 0
    assert perfect["r2"] == 1
    assert perfect["spearman"] == pytest.approx(1)
    assert perfect["constant_prediction_spearman_zeroed"] is False
    assert constant["spearman"] == 0
    assert constant["constant_prediction_spearman_zeroed"] is True


def test_inner_parameter_selection_obeys_frozen_metric_and_complexity_order() -> None:
    evidence = [
        ParameterEvidence({"alpha": 0.1}, [], 0.2, 1.0, 0.1),
        ParameterEvidence({"alpha": 1.0}, [], 0.3, 1.5, 0.0),
        ParameterEvidence({"alpha": 10.0}, [], 0.3, 1.0, 0.0),
        ParameterEvidence({"alpha": 100.0}, [], 0.3, 1.0, 0.0),
    ]

    selected = select_parameter_evidence("ridge_regression", evidence)

    assert selected.hyperparameters == {"alpha": 100.0}


def test_training_row_filter_purges_target_overlap() -> None:
    rows = [
        {
            "feature_session": "2020-12-30",
            "target_session": "2020-12-31",
        },
        {
            "feature_session": "2020-12-31",
            "target_session": "2021-01-04",
        },
    ]

    selected = _training_rows(
        rows,
        date(2020, 1, 1),
        date(2020, 12, 31),
        date(2021, 1, 1),
    )

    assert selected == [rows[0]]


def test_oof_contract_rejects_duplicate_cross_fold_predictions() -> None:
    row = {
        "outer_fold": "fold",
        "model_name": MODEL_NAMES[0],
        "ticker": "2330",
        "feature_session": "2020-01-01",
        "prediction": "1.0",
    }
    verify_oof_rows([row], ("fold",))

    with pytest.raises(ValueError, match="duplicate"):
        verify_oof_rows([row, dict(row)], ("fold",))
