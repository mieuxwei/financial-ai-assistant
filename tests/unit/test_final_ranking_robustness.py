from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from research.evaluation.final_ranking_robustness import (
    BootstrapConfig,
    _regime,
    assign_fold_deciles,
    canonical_f6_config_sha256,
    cluster_bootstrap,
    fit_outer_regime_thresholds,
    lift_ratio,
    load_final_ranking_robustness_config,
)
from research.modeling.final_temporal_evaluation import (
    canonical_f5_config_sha256,
    load_final_temporal_evaluation_config,
)
from research.planning.final_study_protocol import (
    OuterFold,
    canonical_config_sha256,
    load_final_study_config,
)

F1_CONFIG = Path("research/configs/final_volatility_surprise_study.v1.json")
F5_CONFIG = Path("research/configs/final_nested_temporal_evaluation.v1.json")
F6_CONFIG = Path("research/configs/final_ranking_robustness.v1.json")


def test_f6_config_matches_frozen_lineage_and_prohibits_selection() -> None:
    protocol = load_final_study_config(F1_CONFIG)
    f5 = load_final_temporal_evaluation_config(F5_CONFIG)
    config = load_final_ranking_robustness_config(F6_CONFIG)

    assert config.f1_protocol_config_sha256 == canonical_config_sha256(protocol)
    assert config.f5_config_sha256 == canonical_f5_config_sha256(f5)
    assert config.bootstrap.replicates == 1000
    assert config.subgroup_results_used_for_tuning is False
    assert config.final_model_selection_performed_in_f6 is False
    assert config.m7_rerun_allowed is False
    assert len(canonical_f6_config_sha256(config)) == 64


def test_deciles_are_equal_frequency_and_ties_use_date_then_ticker() -> None:
    rows = [
        {
            "model_name": "ridge_regression",
            "outer_fold": "fold",
            "ticker": f"T{9 - index:02d}",
            "feature_session": (date(2025, 1, 1) + timedelta(days=index)).isoformat(),
            "prediction": 1.0,
            "realized_target": float(index),
        }
        for index in range(20)
    ]

    assign_fold_deciles(rows, 10)

    counts = {label: 0 for label in (f"D{value}" for value in range(1, 11))}
    for row in rows:
        counts[row["predicted_decile"]] += 1
    assert set(counts.values()) == {2}
    earliest = min(rows, key=lambda row: (row["feature_session"], row["ticker"]))
    assert earliest["predicted_decile"] == "D10"


def test_lift_uses_ceil_top_count_and_reports_zero_denominator() -> None:
    rows = [
        {
            "prediction": float(index),
            "realized_target": 10.0 if index == 10 else 1.0,
            "feature_session": f"2025-01-{index:02d}",
            "ticker": "T",
        }
        for index in range(1, 11)
    ]
    assert lift_ratio(rows, 0.1) == pytest.approx(10 / 1.9)
    zero = [{**row, "realized_target": 0.0} for row in rows]
    assert lift_ratio(zero, 0.1) is None


def test_regime_cutoffs_use_only_current_outer_training_history() -> None:
    config = load_final_ranking_robustness_config(F6_CONFIG)
    fold = OuterFold.model_validate(
        {
            "name": "outer_2017_2018",
            "train_start": "2011-01-01",
            "train_end": "2016-12-31",
            "evaluation_start": "2017-01-01",
            "evaluation_end": "2018-12-31",
        }
    )
    rows = []
    for index, value in enumerate((1.0, 2.0, 3.0, 4.0, 5.0, 6.0)):
        rows.append(
            {
                "feature_session": f"201{index + 1}-01-02",
                "target_session": f"201{index + 1}-01-03",
                "features": {
                    "volatility_log_return_20": value,
                    "benchmark_volatility_log_return_20": value / 10,
                },
            }
        )
    rows.append(
        {
            "feature_session": "2017-01-02",
            "target_session": "2017-01-03",
            "features": {
                "volatility_log_return_20": 1_000_000.0,
                "benchmark_volatility_log_return_20": 1_000_000.0,
            },
        }
    )

    evidence = fit_outer_regime_thresholds(
        config.model_copy(update={"outer_fold_names": (fold.name,)}),
        rows,
        {fold.name: fold},
    )[fold.name]

    assert evidence["training_row_count"] == 6
    assert evidence["training_targets_precede_evaluation"] is True
    assert evidence["stock_volatility"]["upper_tertile"] < 6
    assert _regime(1.0, evidence["stock_volatility"]) == "LOW"
    assert _regime(6.0, evidence["stock_volatility"]) == "HIGH"


def test_feature_session_bootstrap_is_deterministic_and_does_not_select_model() -> None:
    config = load_final_ranking_robustness_config(F6_CONFIG)
    config = config.model_copy(
        update={
            "bootstrap": BootstrapConfig.model_validate(
                {**config.bootstrap.model_dump(), "replicates": 10}
            )
        }
    )
    rows = []
    for model_index, model in enumerate(config.models):
        for fold_index, fold in enumerate(config.outer_fold_names):
            for row_index in range(20):
                rows.append(
                    {
                        "model_name": model,
                        "outer_fold": fold,
                        "ticker": f"T{row_index % 2}",
                        "feature_session": (
                            date(2020 + fold_index, 1, 1) + timedelta(days=row_index)
                        ).isoformat(),
                        "prediction": float(row_index + model_index / 10),
                        "realized_target": float((row_index % 5) + 1),
                        "stock_regime": "LOW",
                        "market_regime": "LOW",
                    }
                )
    assign_fold_deciles(rows, config.decile_count)

    first = cluster_bootstrap(rows, config)
    second = cluster_bootstrap(rows, config)

    assert first == second
    assert first["replicates_requested"] == 10
    assert all(
        model["metric_intervals"]["mean_outer_spearman"]["valid_replicates"] == 10
        for model in first["models"].values()
    )
