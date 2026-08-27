from __future__ import annotations

import math
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.final_regressors import (
    TemporalFitContext,
    fit_candidate,
    load_final_regression_config,
    verify_f4_contract,
)
from research.planning.final_study_protocol import load_final_study_config

F1_CONFIG = Path("research/configs/final_volatility_surprise_study.v1.json")
F4_CONFIG = Path("research/configs/final_regression_models.v1.json")
DATASET_SHA256 = "d" * 64


def _rows(count: int = 140) -> list[dict[str, object]]:
    start = date(2015, 1, 1)
    rows = []
    for index in range(count):
        session = start + timedelta(days=index)
        values = {
            name: math.sin((index + offset + 1) / 17) * 0.05
            for offset, name in enumerate(FEATURE_NAMES)
        }
        values["return_log_1"] = math.sin(index / 9) * 0.02
        values["volatility_log_return_20"] = 0.01 + (index % 13) * 0.0005
        rows.append(
            {
                "ticker": "2330" if index % 2 == 0 else "0050",
                "feature_session": session.isoformat(),
                "target_session": (session + timedelta(days=1)).isoformat(),
                "information_cutoff": f"{session.isoformat()}T13:30:00+08:00",
                "features": values,
                "target": {
                    "target_version": "next_session_stock_normalized_abs_log_return_v1",
                    "primary": str(0.2 + abs(math.sin(index / 11)) * 2),
                },
            }
        )
    return rows


def _context(count: int = 140) -> TemporalFitContext:
    start = date(2015, 1, 1)
    return TemporalFitContext(
        name="synthetic_training_only",
        training_start=start,
        training_end=start + timedelta(days=count - 1),
        next_validation_or_evaluation_start=start + timedelta(days=count + 1),
    )


def _configs():
    return load_final_regression_config(F4_CONFIG), load_final_study_config(F1_CONFIG)


def test_f4_contract_matches_f1_and_persistence_has_no_fitted_model() -> None:
    config, protocol = _configs()
    verify_f4_contract(config, protocol)
    rows = _rows()

    candidate = fit_candidate(
        config,
        protocol,
        DATASET_SHA256,
        rows,
        _context(),
        "normalized_move_persistence",
        {},
    )
    predictions = candidate.predict_rows(rows[:5])
    expected = np.asarray(
        [
            abs(float(row["features"]["return_log_1"]))
            / float(row["features"]["volatility_log_return_20"])
            for row in rows[:5]
        ]
    )

    assert candidate.model is None
    assert candidate.scaler is None
    assert np.allclose(predictions, expected)
    assert candidate.manifest["validation_or_outer_rows_used_for_fitting"] is False
    assert candidate.manifest["hyperparameter_selection_performed"] is False
    assert candidate.manifest["model_artifact_persisted"] is False


def test_ridge_uses_training_only_scaler_and_reconstructs_deterministically() -> None:
    config, protocol = _configs()
    rows = _rows()
    first = fit_candidate(
        config,
        protocol,
        DATASET_SHA256,
        rows,
        _context(),
        "ridge_regression",
        {"alpha": 1.0},
    )
    second = fit_candidate(
        config,
        protocol,
        DATASET_SHA256,
        deepcopy(rows),
        _context(),
        "ridge_regression",
        {"alpha": 1.0},
    )

    assert first.manifest == second.manifest
    assert np.array_equal(first.predict_rows(rows), second.predict_rows(rows))
    assert first.scaler is not None
    assert np.allclose(
        first.scaler.mean_,
        np.asarray([[row["features"][name] for name in FEATURE_NAMES] for row in rows]).mean(
            axis=0
        ),
    )
    assert np.all(first.predict_rows(rows) >= 0)


def test_hgb_is_deterministic_and_uses_no_implicit_validation_fraction() -> None:
    config, protocol = _configs()
    rows = _rows()
    parameters = {
        "learning_rate": 0.03,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 20,
        "l2_regularization": 0.0,
        "early_stopping": False,
        "random_state": 20260827,
    }
    first = fit_candidate(
        config,
        protocol,
        DATASET_SHA256,
        rows,
        _context(),
        "hist_gradient_boosting_regressor",
        parameters,
    )
    second = fit_candidate(
        config,
        protocol,
        DATASET_SHA256,
        rows,
        _context(),
        "hist_gradient_boosting_regressor",
        parameters,
    )

    assert first.manifest == second.manifest
    assert np.array_equal(first.predict_rows(rows), second.predict_rows(rows))
    assert first.model.get_params()["early_stopping"] is False
    assert first.scaler is None


def test_f4_rejects_parameters_outside_f1_and_temporal_overlap() -> None:
    config, protocol = _configs()
    rows = _rows()
    with pytest.raises(ValueError, match="outside F1 grid"):
        fit_candidate(
            config,
            protocol,
            DATASET_SHA256,
            rows,
            _context(),
            "ridge_regression",
            {"alpha": 999.0},
        )

    context = _context()
    context = context.model_copy(
        update={"next_validation_or_evaluation_start": context.training_end}
    )
    with pytest.raises(ValueError, match="training must end before"):
        fit_candidate(
            config,
            protocol,
            DATASET_SHA256,
            rows,
            context,
            "ridge_regression",
            {"alpha": 1.0},
        )


def test_f4_rejects_duplicate_or_future_feature_training_rows() -> None:
    config, protocol = _configs()
    rows = _rows()
    duplicate = [*rows, deepcopy(rows[0])]
    with pytest.raises(ValueError, match="duplicate"):
        fit_candidate(
            config,
            protocol,
            DATASET_SHA256,
            duplicate,
            _context(),
            "ridge_regression",
            {"alpha": 1.0},
        )

    future = deepcopy(rows)
    future[0]["features"]["future_return"] = 1.0
    with pytest.raises(ValueError, match="feature contract"):
        fit_candidate(
            config,
            protocol,
            DATASET_SHA256,
            future,
            _context(),
            "ridge_regression",
            {"alpha": 1.0},
        )
