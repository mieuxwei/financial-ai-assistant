from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig
from research.evaluation.sealed_risk_test import (
    EXPECTED_CANDIDATE_MANIFEST_SHA256,
    RiskSealedTestConfig,
    _apply_frozen_platt,
    _realized_risk_summary,
    _reconstruct_logistic,
    claim_sealed_test_opening,
)
from research.modeling.baselines import RiskBaselineConfig
from research.risk_labels.protocol import RiskLabelConfig, _build_ticker_drafts


def _sealed_config(**overrides: object) -> RiskSealedTestConfig:
    values: dict[str, object] = {
        "schema_version": "risk-sealed-test-config-v1",
        "protocol_version": "risk-sealed-test-v1",
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
        "market_dataset_sha256": "1" * 64,
        "threshold_artifact_sha256": "2" * 64,
        "pretest_feature_dataset_sha256": "3" * 64,
        "label_config_sha256": "4" * 64,
        "feature_config_sha256": "5" * 64,
        "baseline_config_sha256": "6" * 64,
        "tree_model_config_sha256": "7" * 64,
        "selected_model": "logistic_regression",
        "selected_calibration": "platt",
        "selected_threshold": 0.1,
        "test_start": "2025-01-01",
        "test_end": "2026-08-26",
        "minimum_test_rows": 10,
        "minimum_test_rows_per_ticker": 2,
        "calibration_bins": 5,
        "evaluation_sequence": 1,
        "model_or_threshold_selection_allowed": False,
        "repeat_evaluation_allowed": False,
    }
    values.update(overrides)
    return RiskSealedTestConfig.model_validate(values)


def _baseline_config() -> RiskBaselineConfig:
    return RiskBaselineConfig.model_validate(
        {
            "schema_version": "risk-baseline-config-v1",
            "experiment_version": "risk-baselines-v1",
            "feature_dataset_version": "risk-feature-dataset-v1",
            "train_split": "train",
            "evaluation_split": "validation",
            "normal_label": "NORMAL",
            "high_risk_label": "HIGH_RISK",
            "feature_names": [
                "return_log_1",
                "return_log_5",
                "return_log_10",
                "return_log_20",
                "overnight_gap_log_1",
                "close_ma_deviation_5",
                "close_ma_deviation_20",
                "volume_log_change_1p_1",
                "volume_zscore_20",
                "zero_volume_flag",
                "volatility_log_return_5",
                "volatility_log_return_20",
                "high_low_log_range_1",
                "atr_14_normalized",
                "parkinson_mean_5",
                "rsi_14",
                "macd_12_26_normalized",
                "macd_signal_9_normalized",
                "benchmark_return_log_1",
                "benchmark_return_log_20",
                "benchmark_volatility_log_return_20",
                "stock_minus_benchmark_return_log_1",
                "benchmark_drawdown_20",
            ],
            "decision_threshold": 0.5,
            "calibration_bins": 5,
            "minimum_training_rows": 10,
            "minimum_validation_rows": 5,
            "minimum_training_positive_rows": 2,
            "scaler_with_mean": True,
            "scaler_with_std": True,
            "logistic": {
                "c": 1.0,
                "l1_ratio": 0.0,
                "solver": "lbfgs",
                "class_weight": "balanced",
                "max_iter": 500,
                "tolerance": 0.000001,
                "random_state": 20260827,
            },
            "sealed_test_allowed": False,
            "validation_used_for_fitting": False,
            "hyperparameter_selection_performed": False,
        }
    )


def _label_config() -> RiskLabelConfig:
    return RiskLabelConfig.model_validate(
        {
            "schema_version": "next-session-volatility-risk-config-v1",
            "protocol_version": "next-session-volatility-risk-v1",
            "market_timezone": "Asia/Taipei",
            "information_cutoff": "13:30:00",
            "primary_outcome": "next_normalized_abs_log_return",
            "trailing_volatility_sessions": 2,
            "trailing_volatility_ddof": 0,
            "threshold_fit_split": "train",
            "threshold_quantile": "0.8",
            "quantile_method": "linear",
            "label_comparison": "greater_than_or_equal",
            "high_risk_label": "HIGH_RISK",
            "normal_label": "NORMAL",
            "materialized_splits": ["train", "validation"],
            "minimum_training_rows": 1,
            "minimum_training_rows_per_ticker": 1,
            "minimum_validation_rows_per_ticker": 1,
            "secondary_outcomes": [
                "next_abs_log_return",
                "next_high_low_log_range",
                "next_parkinson_volatility",
            ],
        }
    )


def test_opening_intent_is_one_time_and_immutable(tmp_path: Path) -> None:
    path = tmp_path / "opening.json"
    first = claim_sealed_test_opening(path, _sealed_config())

    assert first["evaluation_sequence"] == 1
    assert first["repeat_evaluation_allowed"] is False
    with pytest.raises(FileExistsError, match="repeat evaluation refused"):
        claim_sealed_test_opening(path, _sealed_config())


def test_frozen_candidate_hash_threshold_and_period_cannot_drift() -> None:
    with pytest.raises(ValidationError, match="candidate manifest hash"):
        _sealed_config(candidate_manifest_sha256="a" * 64)
    with pytest.raises(ValidationError, match="threshold"):
        _sealed_config(selected_threshold=0.2)
    with pytest.raises(ValidationError, match="period"):
        _sealed_config(test_end="2026-08-25")


def test_default_label_builder_excludes_test_and_explicit_m7_builder_allows_it() -> None:
    start = date(2024, 12, 1)
    sessions = [start + timedelta(days=index) for index in range(50)]
    market_config = RiskMarketDatasetConfig.model_validate(
        {
            "schema_version": "risk-market-dataset-config-v1",
            "dataset_version": "risk-market-dataset-v1",
            "market_timezone": "Asia/Taipei",
            "stock_source": "yahoo",
            "stock_source_terms_url": "https://example.test/yahoo",
            "benchmark_dataset_id": "TaiwanStockTotalReturnIndex",
            "benchmark_id": "TAIEX",
            "benchmark_source": "FinMind",
            "benchmark_source_terms_url": "https://example.test/finmind",
            "snapshot_start": sessions[0].isoformat(),
            "train_start": sessions[2].isoformat(),
            "train_end": sessions[14].isoformat(),
            "validation_start": sessions[15].isoformat(),
            "validation_end": sessions[30].isoformat(),
            "test_start": sessions[31].isoformat(),
            "test_end": sessions[-1].isoformat(),
            "minimum_warmup_sessions": 1,
            "minimum_train_sessions": 1,
            "minimum_validation_sessions": 1,
            "minimum_test_sessions": 1,
            "maximum_missing_session_ratio": 0.1,
            "universe": [
                {"ticker": "2330", "provider_symbol": "2330.TW", "name": "台積電"}
            ],
        }
    )
    bars = {}
    for index, session in enumerate(sessions):
        close = 100 + index + (index % 3) / 10
        bars[session] = {
            "trading_date": session.isoformat(),
            "open": str(close - 0.2),
            "high": str(close + 1),
            "low": str(close - 1),
            "close": str(close),
            "adjusted_close": str(close),
            "volume": 1000 + index,
        }
    ordinary, ordinary_excluded = _build_ticker_drafts(
        ticker="2330",
        bars=bars,
        benchmark_sessions=sessions,
        market_config=market_config,
        config=_label_config(),
    )
    sealed, _ = _build_ticker_drafts(
        ticker="2330",
        bars=bars,
        benchmark_sessions=sessions,
        market_config=market_config,
        config=_label_config(),
        materialized_splits={"test"},
        allow_sealed_test=True,
    )

    assert ordinary and all(row["split"] in {"train", "validation"} for row in ordinary)
    assert ordinary_excluded["sealed_test_not_materialized"] > 0
    assert sealed and all(row["split"] == "test" for row in sealed)


def test_logistic_reconstruction_and_platt_application_are_deterministic() -> None:
    rng = np.random.default_rng(20260827)
    x_train = rng.normal(size=(80, 23))
    y_train = np.asarray([index % 5 == 0 for index in range(80)], dtype=np.int8)
    x_test = rng.normal(size=(20, 23))

    first_probability, first_state, first_train = _reconstruct_logistic(
        x_train, y_train, x_test, _baseline_config()
    )
    second_probability, second_state, second_train = _reconstruct_logistic(
        x_train, y_train, x_test, _baseline_config()
    )
    calibrated = _apply_frozen_platt(
        first_probability,
        {"coefficient": 0.8, "intercept": -2.0},
    )

    assert first_state == second_state
    assert np.array_equal(first_probability, second_probability)
    assert np.array_equal(first_train, second_train)
    assert np.all((calibrated > 0) & (calibrated < 1))


def test_realized_risk_summary_separates_predictions_without_raw_output() -> None:
    rows = [
        {
            "predicted_label": "NORMAL",
            "target": {
                "continuous_risk_outcome": "0.5",
                "next_abs_log_return": "0.01",
                "next_high_low_log_range": "0.02",
                "next_parkinson_volatility": "0.012",
            },
        },
        {
            "predicted_label": "HIGH_RISK",
            "target": {
                "continuous_risk_outcome": "2.0",
                "next_abs_log_return": "0.04",
                "next_high_low_log_range": "0.05",
                "next_parkinson_volatility": "0.03",
            },
        },
    ]

    summary = _realized_risk_summary(rows)

    assert summary["HIGH_RISK"]["mean_continuous_risk_outcome"] == 2.0
    assert summary["NORMAL"]["mean_continuous_risk_outcome"] == 0.5
    assert "rows" not in summary
