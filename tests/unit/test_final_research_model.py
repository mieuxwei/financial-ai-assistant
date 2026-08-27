from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pipelines.features.risk_builder import FEATURE_NAMES
from research.modeling.final_regressors import (
    canonical_f4_config_sha256,
    load_final_regression_config,
)
from research.modeling.final_research_model import (
    ARTIFACT_VERSION,
    canonical_f7_config_sha256,
    load_final_model_freeze_config,
    predict_from_artifact,
    select_final_model,
    verify_model_artifact,
)
from research.planning.final_study_protocol import (
    canonical_config_sha256,
    load_final_study_config,
)

F1_CONFIG = Path("research/configs/final_volatility_surprise_study.v1.json")
F4_CONFIG = Path("research/configs/final_regression_models.v1.json")
F7_CONFIG = Path("research/configs/final_model_freeze.v1.json")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _artifact() -> dict[str, object]:
    size = len(FEATURE_NAMES)
    content = {
        "schema_version": ARTIFACT_VERSION,
        "inference_contract_version": "volatility-surprise-inference-v1",
        "artifact_format": "SAFE_JSON_NO_PICKLE",
        "model_name": "ridge_regression",
        "model_version": ARTIFACT_VERSION,
        "feature_pipeline_version": "risk-features-v1",
        "feature_names": list(FEATURE_NAMES),
        "target_version": "next_session_stock_normalized_abs_log_return_v1",
        "target_transform": "log1p",
        "inverse_transform": "maximum_zero_expm1",
        "prediction_quantum": "0.000000000001",
        "selected_hyperparameters": {"alpha": 100.0},
        "scaler_mean": [0.0] * size,
        "scaler_scale": [1.0] * size,
        "coefficient": [1.0] + [0.0] * (size - 1),
        "intercept": 0.0,
        "historical_reference": {
            "row_count": 3,
            "percentile_output_decimals": 6,
            "band_cutoffs": ["0.500000000000", "0.800000000000", "0.950000000000"],
            "band_labels": ["LOW", "MODERATE", "HIGH", "VERY_HIGH"],
            "sorted_predictions": ["0.000000000000", "0.500000000000", "1.000000000000"],
        },
        "lineage": {},
        "training": {},
        "research_claim_boundary": {},
        "final_model_selected": True,
        "model_artifact_persisted": True,
        "deployed": False,
        "m7_rerun_performed": False,
    }
    return {**content, "sha256": _hash(content)}


def test_f7_config_matches_frozen_f1_f4_and_safe_json_contract() -> None:
    protocol = load_final_study_config(F1_CONFIG)
    regression = load_final_regression_config(F4_CONFIG)
    config = load_final_model_freeze_config(F7_CONFIG)

    assert config.f1_protocol_config_sha256 == canonical_config_sha256(protocol)
    assert config.f4_config_sha256 == canonical_f4_config_sha256(regression)
    assert config.artifact_format == "SAFE_JSON_NO_PICKLE"
    assert config.selection_rule.expected_selected_model == "ridge_regression"
    assert config.deploy_in_f7 is False
    assert len(canonical_f7_config_sha256(config)) == 64


def test_frozen_practical_tie_rule_selects_ridge_by_lower_mae() -> None:
    config = load_final_model_freeze_config(F7_CONFIG)
    analysis = {
        "model_summaries": {
            "normalized_move_persistence": {
                "mean_spearman": 0.06,
                "mean_mae": 0.72,
                "worst_spearman": 0.0,
            },
            "ridge_regression": {
                "mean_spearman": 0.194,
                "mean_mae": 0.5473,
                "worst_spearman": 0.109,
            },
            "hist_gradient_boosting_regressor": {
                "mean_spearman": 0.1863,
                "mean_mae": 0.5480,
                "worst_spearman": 0.135,
            },
        }
    }

    selected = select_final_model(config, analysis)

    assert selected["practical_tie_candidates"] == [
        "hist_gradient_boosting_regressor",
        "ridge_regression",
    ]
    assert selected["selected_model"] == "ridge_regression"
    assert selected["tie_broken_by"] == "lower_mean_outer_mae"
    assert selected["single_period_or_subgroup_selection_used"] is False


def test_safe_json_inference_returns_score_percentile_and_band() -> None:
    artifact = _artifact()
    features = {name: 0.0 for name in FEATURE_NAMES}
    features[FEATURE_NAMES[0]] = 0.6931471805599453

    result = predict_from_artifact(
        artifact,
        "2330",
        "2026-08-28",
        "2026-08-28T13:30:00+08:00",
        features,
    )

    assert result["predicted_volatility_surprise"] == "1.000000000000"
    assert result["historical_percentile"] == 100.0
    assert result["risk_band"] == "VERY_HIGH"
    assert set(result) == {
        "ticker",
        "as_of_date",
        "information_cutoff",
        "predicted_volatility_surprise",
        "historical_percentile",
        "risk_band",
        "model_version",
        "feature_pipeline_version",
    }


def test_artifact_hash_feature_contract_and_timezone_are_enforced() -> None:
    artifact = _artifact()
    verify_model_artifact(artifact)
    tampered = deepcopy(artifact)
    tampered["coefficient"][0] = 99.0
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_model_artifact(tampered)

    features = {name: 0.0 for name in FEATURE_NAMES}
    with pytest.raises(ValueError, match="timezone-aware"):
        predict_from_artifact(
            artifact, "2330", "2026-08-28", "2026-08-28T13:30:00", features
        )
    missing = dict(features)
    missing.pop(FEATURE_NAMES[0])
    with pytest.raises(ValueError, match="frozen contract"):
        predict_from_artifact(
            artifact,
            "2330",
            "2026-08-28",
            "2026-08-28T13:30:00+08:00",
            missing,
        )
