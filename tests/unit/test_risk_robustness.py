import hashlib
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest

from research.evaluation.risk_robustness import (
    RiskRobustnessConfig,
    analyze_risk_robustness,
    verify_m7_chain,
)


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _sealed_evaluation() -> dict[str, object]:
    start = date(2025, 1, 2)
    rows = []
    for index in range(120):
        session = start + timedelta(days=index // 4)
        actual_high = index % 5 == 0
        probability = 0.16 if index % 4 == 0 else 0.06
        rows.append(
            {
                "ticker": f"T{index % 4}",
                "feature_session": session.isoformat(),
                "split": "test",
                "features": {
                    "volatility_log_return_20": 0.01 + (index % 9) * 0.002,
                    "benchmark_volatility_log_return_20": 0.008 + (index % 7) * 0.001,
                },
                "target": {
                    "risk_label": "HIGH_RISK" if actual_high else "NORMAL",
                    "continuous_risk_outcome": str(2.0 if actual_high else 0.5),
                    "next_abs_log_return": str(0.03 if actual_high else 0.01),
                    "next_high_low_log_range": str(0.04 if actual_high else 0.02),
                    "next_parkinson_volatility": str(0.025 if actual_high else 0.012),
                },
                "raw_probability": probability + 0.1,
                "calibrated_probability": probability,
                "predicted_label": "HIGH_RISK" if probability >= 0.1 else "NORMAL",
            }
        )
    content: dict[str, object] = {
        "schema_version": "risk-sealed-test-evaluation-v1",
        "protocol_version": "risk-sealed-test-v1",
        "candidate_manifest_sha256": "c" * 64,
        "opening_intent_sha256": "placeholder",
        "market_dataset_sha256": "m" * 64,
        "threshold_artifact_sha256": "t" * 64,
        "test_start": "2025-01-01",
        "test_end": "2026-08-26",
        "evaluation_sequence": 1,
        "model_or_threshold_selection_performed": False,
        "rows": rows,
    }
    return {**content, "sha256": _hash(content)}


def _pretest_dataset() -> dict[str, object]:
    rows = [
        {
            "features": {
                "volatility_log_return_20": 0.005 + (index % 20) * 0.001,
                "benchmark_volatility_log_return_20": 0.004 + (index % 15) * 0.001,
            }
        }
        for index in range(200)
    ]
    content: dict[str, object] = {
        "schema_version": "risk-feature-dataset-v1",
        "rows": rows,
    }
    return {**content, "sha256": _hash(content)}


def _config(
    evaluation: dict[str, object],
    pretest: dict[str, object],
    **overrides: object,
) -> RiskRobustnessConfig:
    values: dict[str, object] = {
        "schema_version": "risk-robustness-config-v1",
        "protocol_version": "risk-robustness-v1",
        "sealed_evaluation_sha256": evaluation["sha256"],
        "opening_intent_sha256": "1" * 64,
        "completion_record_sha256": "2" * 64,
        "candidate_manifest_sha256": "c" * 64,
        "pretest_feature_dataset_sha256": pretest["sha256"],
        "selected_threshold": 0.1,
        "probability_bin_edges": [0.0, 0.1, 0.2, 1.0],
        "regime_quantiles": [1 / 3, 2 / 3],
        "stock_regime_feature": "volatility_log_return_20",
        "market_regime_feature": "benchmark_volatility_log_return_20",
        "minimum_stratum_rows": 10,
        "minimum_stratum_positive_rows": 2,
        "bootstrap_iterations": 100,
        "bootstrap_seed": 20260827,
        "bootstrap_cluster": "feature_session",
        "bootstrap_confidence": 0.95,
        "m7_rerun_allowed": False,
        "model_or_threshold_selection_allowed": False,
    }
    values.update(overrides)
    return RiskRobustnessConfig.model_validate(values)


def test_robustness_analysis_is_deterministic_and_contains_no_rows() -> None:
    evaluation = _sealed_evaluation()
    pretest = _pretest_dataset()
    config = _config(evaluation, pretest)

    first, report = analyze_risk_robustness(config, evaluation, pretest)
    second, _ = analyze_risk_robustness(config, evaluation, pretest)

    assert first == second
    assert first["m7_rerun_performed"] is False
    assert first["model_or_threshold_selection_performed"] is False
    assert first["rows_persisted"] is False
    assert "rows" not in report
    assert set(report["ticker"]) == {"T0", "T1", "T2", "T3"}
    assert report["cluster_bootstrap"]["iterations_valid"] == 100
    assert report["realized_risk_separation"]["overall"]["HIGH_RISK"]["row_count"] > 0


def test_small_strata_are_marked_insufficient_instead_of_overclaimed() -> None:
    evaluation = _sealed_evaluation()
    pretest = _pretest_dataset()
    config = _config(evaluation, pretest, minimum_stratum_rows=1000)

    _, report = analyze_risk_robustness(config, evaluation, pretest)

    assert all(
        value["status"] == "INSUFFICIENT_FOR_FULL_METRICS"
        for value in report["ticker"].values()
    )
    assert all(value["metrics"] is None for value in report["ticker"].values())


def test_evaluation_hash_or_stored_threshold_prediction_drift_is_rejected() -> None:
    evaluation = _sealed_evaluation()
    pretest = _pretest_dataset()
    config = _config(evaluation, pretest)
    tampered = deepcopy(evaluation)
    tampered["rows"][0]["calibrated_probability"] = 0.99
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        analyze_risk_robustness(config, tampered, pretest)

    drifted = deepcopy(evaluation)
    drifted["rows"][0]["predicted_label"] = "NORMAL"
    content = {key: value for key, value in drifted.items() if key != "sha256"}
    drifted["sha256"] = _hash(content)
    drifted_config = _config(drifted, pretest)
    with pytest.raises(ValueError, match="frozen threshold"):
        analyze_risk_robustness(drifted_config, drifted, pretest)


def test_m7_chain_verification_requires_one_linked_evaluation() -> None:
    evaluation = _sealed_evaluation()
    pretest = _pretest_dataset()
    opening_content = {
        "evaluation_sequence": 1,
        "candidate_manifest_sha256": "c" * 64,
    }
    opening = {**opening_content, "sha256": _hash(opening_content)}
    evaluation_content = {key: value for key, value in evaluation.items() if key != "sha256"}
    evaluation_content["opening_intent_sha256"] = opening["sha256"]
    evaluation = {**evaluation_content, "sha256": _hash(evaluation_content)}
    m7_report = {
        "sealed_test_evaluations": 1,
        "model_or_threshold_selection_performed": False,
    }
    completion_content = {
        "evaluation_sequence": 1,
        "candidate_manifest_sha256": "c" * 64,
        "opening_intent_sha256": opening["sha256"],
        "sealed_test_evaluation_sha256": evaluation["sha256"],
        "report_sha256": _hash(m7_report),
        "repeat_evaluation_allowed": False,
    }
    completion = {**completion_content, "sha256": _hash(completion_content)}
    config = _config(
        evaluation,
        pretest,
        opening_intent_sha256=opening["sha256"],
        completion_record_sha256=completion["sha256"],
    )

    verify_m7_chain(config, evaluation, opening, completion, m7_report, pretest)

    bad_completion = deepcopy(completion)
    bad_completion["sealed_test_evaluation_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_m7_chain(
            config,
            evaluation,
            opening,
            bad_completion,
            m7_report,
            pretest,
        )
