from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from research.evaluation.operating_points import _hash
from research.evaluation.regime_thresholds import (
    REGIMES,
    _regime_threshold_tables,
    _verify_inputs,
    assign_development_regimes,
    load_config,
    select_regime_policy,
)
from research.modeling.temporal_validation import RiskTemporalValidationConfig

CONFIG_PATH = Path("research/configs/post_m8_regime_thresholds.v1.json")


def _temporal_config() -> RiskTemporalValidationConfig:
    return RiskTemporalValidationConfig.model_validate(
        {
            "schema_version": "risk-temporal-validation-config-v1",
            "protocol_version": "risk-temporal-validation-v1",
            "feature_dataset_version": "risk-feature-dataset-v1",
            "baseline_config_sha256": "a" * 64,
            "tree_model_config_sha256": "b" * 64,
            "normal_label": "NORMAL",
            "high_risk_label": "HIGH_RISK",
            "candidate_models": [
                "logistic_regression",
                "random_forest",
                "hist_gradient_boosting",
            ],
            "folds": [
                {
                    "name": "history",
                    "train_end": "2018-12-31",
                    "evaluation_start": "2019-01-01",
                    "evaluation_end": "2019-12-31",
                },
                {
                    "name": "fold_2020",
                    "train_end": "2019-12-31",
                    "evaluation_start": "2020-01-01",
                    "evaluation_end": "2020-12-31",
                },
                {
                    "name": "fold_2021",
                    "train_end": "2020-12-31",
                    "evaluation_start": "2021-01-01",
                    "evaluation_end": "2021-12-31",
                },
            ],
            "minimum_fold_training_rows": 1,
            "minimum_fold_evaluation_rows": 1,
            "minimum_fold_positive_rows": 1,
            "purge_target_overlap": True,
            "embargo_sessions": 0,
            "calibration_method": "prequential_platt_or_identity",
            "platt_c": 1.0,
            "probability_clip": 0.000001,
            "calibration_bins": 10,
            "model_selection_primary": "mean_fold_pr_auc",
            "model_selection_secondary": "mean_fold_mcc",
            "calibration_selection_metric": "pooled_prequential_brier",
            "minimum_calibration_brier_improvement": 0.0,
            "threshold_candidates": [0.1, 0.2],
            "minimum_high_risk_recall": 0.5,
            "threshold_selection_metric": "mcc_subject_to_minimum_recall",
            "final_fit_end": "2021-12-31",
            "sealed_test_start": "2022-01-01",
            "sealed_test_allowed": False,
        }
    )


def _feature_row(ticker: str, feature: str, target: str, volatility: float) -> dict[str, object]:
    return {
        "ticker": ticker,
        "feature_session": feature,
        "split": "train",
        "features": {"volatility_log_return_20": volatility},
        "target": {"target_session": target, "risk_label": "HIGH_RISK"},
    }


def test_fold_regimes_use_only_earlier_training_history() -> None:
    config = load_config(CONFIG_PATH)
    temporal = _temporal_config()
    feature_rows = [
        _feature_row("A", "2018-01-01", "2018-01-02", 1.0),
        _feature_row("B", "2019-06-01", "2019-06-02", 2.0),
        _feature_row("C", "2020-06-01", "2020-06-02", 100.0),
        _feature_row("D", "2021-06-01", "2021-06-02", 200.0),
    ]
    development_rows = [
        {
            "ticker": "C",
            "feature_session": "2020-06-01",
            "target_session": "2020-06-02",
            "source_split": "train",
            "fold": "fold_2020",
            "calibrated_probability": 0.2,
            "high_risk_label": 1,
            "volatility_log_return_20": 100.0,
        },
        {
            "ticker": "D",
            "feature_session": "2021-06-01",
            "target_session": "2021-06-02",
            "source_split": "train",
            "fold": "fold_2021",
            "calibrated_probability": 0.2,
            "high_risk_label": 1,
            "volatility_log_return_20": 200.0,
        },
    ]

    assigned, evidence = assign_development_regimes(
        config, temporal, feature_rows, development_rows
    )

    assert [row["regime"] for row in assigned] == ["HIGH", "HIGH"]
    assert evidence["folds"][0]["training_row_count"] == 2
    assert evidence["folds"][0]["upper_tertile"] < 100.0
    assert evidence["folds"][0]["training_target_precedes_evaluation"] is True
    assert (
        evidence["final_prospective_policy_cutoffs"]["used_to_reassign_development_rows"]
        is False
    )


def test_selection_is_deterministic_and_honors_constraints() -> None:
    labels = np.asarray(([0] * 70 + [1] * 30) * 3, dtype=np.int8)
    probabilities = np.asarray(([0.02] * 40 + [0.15] * 30 + [0.08] * 10 + [0.20] * 20) * 3)
    regimes = np.asarray([regime for regime in REGIMES for _ in range(100)])
    tables = _regime_threshold_tables(labels, probabilities, regimes, [0.05, 0.10, 0.20])
    constraints = {
        "minimum_overall_recall": 0.5,
        "minimum_overall_specificity": 0.5,
        "minimum_each_regime_recall": 0.35,
        "minimum_each_regime_specificity": 0.35,
        "minimum_rows_per_regime": 50,
        "minimum_positive_rows_per_regime": 10,
    }

    first, first_count = select_regime_policy(tables, constraints)
    second, second_count = select_regime_policy(tables, constraints)

    assert first == second
    assert first_count == second_count
    assert first_count > 0
    assert first is not None


def test_input_guard_rejects_tampering_sealed_rows_and_forbidden_hash() -> None:
    config = load_config(CONFIG_PATH)
    feature_content = {"rows": []}
    feature = {**feature_content, "sha256": _hash(feature_content)}
    development_content = {
        "purpose": "M10_M11_DEVELOPMENT_SELECTION_ONLY",
        "feature_dataset_sha256": feature["sha256"],
        "sealed_test_rows_used": 0,
        "m7_m8_m9_labels_or_outcomes_used": False,
        "rows": [],
    }
    development = {**development_content, "sha256": _hash(development_content)}
    report = {
        "development_oof_dataset_sha256": development["sha256"],
        "analysis_sha256": "c" * 64,
        "result_scope": "DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT",
    }
    _verify_inputs(config, feature, development, report)

    sealed = deepcopy(development)
    sealed["sealed_test_rows_used"] = 1
    with pytest.raises(ValueError, match="sealed rows"):
        _verify_inputs(config, feature, sealed, report)

    forbidden_report = {**report, "analysis_sha256": config["forbidden_evidence_sha256"][0]}
    with pytest.raises(ValueError, match="forbidden M7/M8"):
        _verify_inputs(config, feature, development, forbidden_report)


def test_m11_code_never_invokes_sealed_test_or_trains_separate_models() -> None:
    source = Path("research/evaluation/regime_thresholds.py").read_text(encoding="utf-8")
    job = Path("jobs/regime_thresholds.py").read_text(encoding="utf-8")

    assert "risk_sealed_test" not in source + job
    assert "sealed-test-v1/evaluation" not in source + job
    assert "fit_predict_candidate" not in source + job
    assert "run_temporal_validation(" not in source + job
