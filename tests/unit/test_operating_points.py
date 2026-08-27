from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from research.evaluation.operating_points import (
    _hash,
    _threshold_grid,
    _verify_selection_row,
    analyze_operating_points,
    load_config,
    select_operating_mode,
)

CONFIG_PATH = Path("research/configs/post_m8_operating_points.v1.json")


def _candidate(
    threshold: float,
    precision: float,
    recall: float,
    specificity: float,
    mcc: float,
) -> dict[str, object]:
    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "mcc": mcc,
        "f1": 2 * precision * recall / (precision + recall),
        "balanced_accuracy": (recall + specificity) / 2,
    }


def _development_dataset(config: dict[str, object]) -> dict[str, object]:
    rows = []
    for index in range(200):
        label = int(index % 10 == 0)
        probability = 0.20 if index % 8 == 0 else 0.04 + (index % 5) * 0.02
        rows.append(
            {
                "ticker": f"T{index % 4}",
                "feature_session": f"2024-01-{index % 28 + 1:02d}",
                "target_session": f"2024-02-{index % 28 + 1:02d}",
                "source_split": "validation",
                "fold": "wf_2024",
                "calibrated_probability": probability,
                "high_risk_label": label,
                "volatility_log_return_20": 0.01,
            }
        )
    content = {
        "schema_version": "post-m8-development-oof-dataset-v1",
        "purpose": "M10_M11_DEVELOPMENT_SELECTION_ONLY",
        "sealed_test_rows_used": 0,
        "m7_m8_m9_labels_or_outcomes_used": False,
        "rows": rows,
    }
    return {**content, "sha256": _hash(content)}


def test_frozen_grid_contains_exactly_50_cent_thresholds() -> None:
    config = load_config(CONFIG_PATH)

    grid = _threshold_grid(config["threshold_grid"])

    assert len(grid) == 50
    assert grid[0] == 0.01
    assert grid[-1] == 0.50
    assert 0.10 in grid


def test_predeclared_modes_apply_constraints_and_objectives() -> None:
    config = load_config(CONFIG_PATH)
    candidates = [
        _candidate(0.05, 0.11, 0.90, 0.45, 0.05),
        _candidate(0.10, 0.13, 0.70, 0.60, 0.20),
        _candidate(0.20, 0.25, 0.50, 0.80, 0.30),
    ]

    screening = select_operating_mode(
        candidates, "screening", config["operating_modes"]["screening"]
    )
    balanced = select_operating_mode(
        candidates, "balanced", config["operating_modes"]["balanced"]
    )
    precision = select_operating_mode(
        candidates, "precision", config["operating_modes"]["precision"]
    )

    assert screening["selected"]["threshold"] == 0.10
    assert balanced["selected"]["threshold"] == 0.20
    assert precision["selected"]["threshold"] == 0.20


def test_no_eligible_candidate_is_inconclusive() -> None:
    config = load_config(CONFIG_PATH)
    candidates = [_candidate(0.05, 0.01, 0.10, 0.10, 0.0)]

    result = select_operating_mode(
        candidates, "screening", config["operating_modes"]["screening"]
    )

    assert result["status"] == "INCONCLUSIVE_NO_POLICY_SELECTED"
    assert result["selected"] is None


def test_selection_rows_reject_test_or_post_2024_data() -> None:
    config = load_config(CONFIG_PATH)
    with pytest.raises(ValueError, match="not train/validation"):
        _verify_selection_row(
            {"source_split": "test", "target_session": "2024-01-02"}, config
        )
    with pytest.raises(ValueError, match="sealed-test time"):
        _verify_selection_row(
            {"source_split": "validation", "target_session": "2025-01-02"}, config
        )


def test_analysis_is_raw_free_and_development_only() -> None:
    config = load_config(CONFIG_PATH)
    dataset = _development_dataset(config)

    first, report = analyze_operating_points(config, dataset, {"matched_m6": True})
    second, _ = analyze_operating_points(config, dataset, {"matched_m6": True})

    assert first == second
    assert "rows" not in report
    assert first["sealed_test_rows_used"] == 0
    assert first["m7_m8_m9_labels_or_outcomes_used"] is False
    assert first["m7_final_candidate_refit_performed"] is False
    assert first["historical_threshold_replaced"] is False
    assert first["result_scope"] == "DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT"


def test_analysis_rejects_tampered_or_sealed_dataset() -> None:
    config = load_config(CONFIG_PATH)
    dataset = _development_dataset(config)
    tampered = deepcopy(dataset)
    tampered["rows"][0]["high_risk_label"] = 1 - tampered["rows"][0]["high_risk_label"]
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        analyze_operating_points(config, tampered, {})

    sealed = deepcopy(dataset)
    sealed["sealed_test_rows_used"] = 1
    content = {key: value for key, value in sealed.items() if key != "sha256"}
    sealed["sha256"] = _hash(content)
    with pytest.raises(ValueError, match="sealed rows"):
        analyze_operating_points(config, sealed, {})


def test_m10_code_does_not_call_m6_full_run_or_sealed_test() -> None:
    source = Path("research/evaluation/operating_points.py").read_text(encoding="utf-8")
    job = Path("jobs/operating_points.py").read_text(encoding="utf-8")

    assert "run_temporal_validation(" not in source + job
    assert "risk_sealed_test" not in source + job
    assert "sealed-test-v1/evaluation" not in source + job
