from __future__ import annotations

import json
from pathlib import Path

M7_EVALUATION_SHA256 = "4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe"
M8_ANALYSIS_SHA256 = "c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b"
M7_PREDICTION_COUNT = 3647
HISTORICAL_M7_THRESHOLD = 0.10


def load_spec(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_post_m8_specs(config_directory: Path) -> None:
    m9 = load_spec(config_directory / "post_m8_conditional_risk.v1.json")
    m10 = load_spec(config_directory / "post_m8_operating_points.v1.json")
    m11 = load_spec(config_directory / "post_m8_regime_thresholds.v1.json")
    m12 = load_spec(config_directory / "post_m8_prospective_validation.v1.json")

    historical = m9["historical_evidence"]
    if historical["m7_sealed_evaluation_sha256"] != M7_EVALUATION_SHA256:
        raise ValueError("M7 evaluation hash changed")
    if historical["m8_analysis_sha256"] != M8_ANALYSIS_SHA256:
        raise ValueError("M8 analysis hash changed")
    if historical["m7_prediction_count"] != M7_PREDICTION_COUNT:
        raise ValueError("M7 prediction count changed")
    if historical["historical_decision_threshold"] != HISTORICAL_M7_THRESHOLD:
        raise ValueError("historical M7 threshold changed")
    if not m9["analysis_only"] or any(
        m9[field]
        for field in (
            "model_refit_allowed",
            "prediction_mutation_allowed",
            "threshold_change_allowed",
            "classifier_feedback_allowed",
        )
    ):
        raise ValueError("M9 must remain analysis-only")

    for name, spec in (("M10", m10), ("M11", m11)):
        source = spec["development_prediction_source"]
        if source["allowed_splits"] != ["train", "validation"]:
            raise ValueError(f"{name} selection inputs are not development-only")
        if source["latest_allowed_target_session"] > "2024-12-31":
            raise ValueError(f"{name} selection period reaches sealed-test time")
        if source["sealed_test_rows_allowed"] or source["m7_or_m8_labels_allowed"]:
            raise ValueError(f"{name} permits historical sealed evidence for selection")
        if set(spec["forbidden_evidence_sha256"]) != {
            M7_EVALUATION_SHA256,
            M8_ANALYSIS_SHA256,
        }:
            raise ValueError(f"{name} forbidden-evidence hashes drifted")

    regime = m11["regime_definition"]
    if regime["feature_available_at"] != "post_close_t":
        raise ValueError("M11 regime is not observable at prediction time")
    if regime["future_or_target_values_allowed"]:
        raise ValueError("M11 regime permits future target values")
    if m11["separate_models_allowed"]:
        raise ValueError("M11 must test thresholds before separate models")

    holdout = m12["holdout_enrollment"]
    if holdout["holdout_features_or_labels_materialized"]:
        raise ValueError("M12 prospective holdout has been opened")
    if holdout["accessible_to_tuning_code"]:
        raise ValueError("M12 prospective holdout is accessible to tuning")
    if not m12["pre_opening_gate"]["policy_manifest_required"]:
        raise ValueError("M12 policy freeze gate is disabled")
    if m12["subgroup_results_used_for_retuning"]:
        raise ValueError("M12 subgroup feedback is enabled")
