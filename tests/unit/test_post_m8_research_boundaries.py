import json
from pathlib import Path

import pytest

from research.evaluation.post_m8_research_boundaries import (
    HISTORICAL_M7_THRESHOLD,
    M7_EVALUATION_SHA256,
    M7_PREDICTION_COUNT,
    M8_ANALYSIS_SHA256,
    load_spec,
    validate_post_m8_specs,
)

CONFIG_DIRECTORY = Path("research/configs")


def test_frozen_post_m8_specs_pass_boundary_validation() -> None:
    validate_post_m8_specs(CONFIG_DIRECTORY)


def test_m9_preserves_historical_hashes_count_and_threshold() -> None:
    spec = load_spec(CONFIG_DIRECTORY / "post_m8_conditional_risk.v1.json")
    evidence = spec["historical_evidence"]

    assert evidence["m7_sealed_evaluation_sha256"] == M7_EVALUATION_SHA256
    assert evidence["m8_analysis_sha256"] == M8_ANALYSIS_SHA256
    assert evidence["m7_prediction_count"] == M7_PREDICTION_COUNT
    assert evidence["historical_decision_threshold"] == HISTORICAL_M7_THRESHOLD
    assert spec["analysis_only"] is True


@pytest.mark.parametrize(
    "filename",
    ["post_m8_operating_points.v1.json", "post_m8_regime_thresholds.v1.json"],
)
def test_threshold_selection_specs_exclude_m7_and_m8_labels(filename: str) -> None:
    spec = load_spec(CONFIG_DIRECTORY / filename)
    source = spec["development_prediction_source"]
    serialized = json.dumps(spec, sort_keys=True)

    assert source["allowed_splits"] == ["train", "validation"]
    assert source["latest_allowed_target_session"] <= "2024-12-31"
    assert source["sealed_test_rows_allowed"] is False
    assert source["m7_or_m8_labels_allowed"] is False
    assert M7_EVALUATION_SHA256 in spec["forbidden_evidence_sha256"]
    assert M8_ANALYSIS_SHA256 in spec["forbidden_evidence_sha256"]
    assert "risk-sealed-test-v1/evaluation.json" not in serialized
    assert "risk-robustness-v1/analysis.json" not in serialized


def test_m11_regime_uses_only_t_known_lagged_state() -> None:
    spec = load_spec(CONFIG_DIRECTORY / "post_m8_regime_thresholds.v1.json")
    regime = spec["regime_definition"]

    assert regime["feature"] == "volatility_log_return_20"
    assert regime["feature_available_at"] == "post_close_t"
    assert regime["lookback_sessions"] == 20
    assert regime["future_or_target_values_allowed"] is False
    assert spec["separate_models_allowed"] is False


def test_m12_holdout_is_unopened_and_inaccessible_to_tuning() -> None:
    spec = load_spec(CONFIG_DIRECTORY / "post_m8_prospective_validation.v1.json")
    holdout = spec["holdout_enrollment"]

    assert spec["status"] == "PROTOCOL_FROZEN_HOLDOUT_NOT_AVAILABLE_NOT_OPENED"
    assert holdout["holdout_features_or_labels_materialized"] is False
    assert holdout["accessible_to_tuning_code"] is False
    assert spec["pre_opening_gate"]["policy_manifest_required"] is True
    assert spec["subgroup_results_used_for_retuning"] is False


def test_public_m7_m8_integrity_statements_remain_frozen() -> None:
    m7 = Path("research/evaluation/m7_risk_sealed_test_result.md").read_text(
        encoding="utf-8"
    )
    m8 = Path("research/evaluation/m8_risk_robustness_result.md").read_text(
        encoding="utf-8"
    )

    assert "Eligible rows: 3,647" in m7
    assert "Decision threshold: frozen 0.10" in m7
    assert M7_EVALUATION_SHA256 in m7
    assert "recall 0.508, precision 0.180, MCC 0.155, PR-AUC 0.189" in m8
    assert M8_ANALYSIS_SHA256 in m8


def test_boundary_validator_rejects_sealed_selection_permission(tmp_path: Path) -> None:
    for source in CONFIG_DIRECTORY.glob("post_m8_*.v1.json"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    path = tmp_path / "post_m8_operating_points.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["development_prediction_source"]["sealed_test_rows_allowed"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="historical sealed evidence"):
        validate_post_m8_specs(tmp_path)
