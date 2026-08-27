from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from research.evaluation import conditional_risk as subject


def _fixtures(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, object], ...]:
    rows = []
    start = date(2025, 1, 2)
    cells = (
        ("LOW", 1, 120),
        ("MIDDLE", 1, 30),
        ("HIGH", 1, 30),
        ("LOW", 0, 30),
        ("MIDDLE", 0, 30),
        ("HIGH", 0, 120),
    )
    regime_values = {"LOW": 0.005, "MIDDLE": 0.015, "HIGH": 0.030}
    regime_baselines = {"LOW": 0.010, "MIDDLE": 0.030, "HIGH": 0.060}
    index = 0
    for regime, predicted, count in cells:
        for _ in range(count):
            prior = regime_values[regime]
            absolute_return = regime_baselines[regime] + 0.005 * predicted
            session = start + timedelta(days=index // 10)
            rows.append(
                {
                    "ticker": f"T{index % 10}",
                    "feature_session": session.isoformat(),
                    "features": {"volatility_log_return_20": prior},
                    "target": {
                        "risk_label": "NORMAL",
                        "next_abs_log_return": absolute_return,
                        "next_high_low_log_range": absolute_return * 1.5,
                        "next_parkinson_volatility": absolute_return * 0.9,
                        "continuous_risk_outcome": absolute_return / prior,
                    },
                    "calibrated_probability": 0.15 if predicted else 0.05,
                    "predicted_label": "HIGH_RISK" if predicted else "NORMAL",
                }
            )
            index += 1
    evaluation_content = {
        "evaluation_sequence": 1,
        "model_or_threshold_selection_performed": False,
        "rows": rows,
    }
    evaluation = {**evaluation_content, "sha256": subject._hash(evaluation_content)}
    m8_content = {
        "sealed_evaluation_sha256": evaluation["sha256"],
        "regime_thresholds": {
            "stock_volatility": {"low_upper": 0.01, "middle_upper": 0.02}
        },
        "m7_rerun_performed": False,
        "model_or_threshold_selection_performed": False,
    }
    m8 = {**m8_content, "sha256": subject._hash(m8_content)}
    monkeypatch.setattr(subject, "M7_EVALUATION_SHA256", evaluation["sha256"])
    monkeypatch.setattr(subject, "M8_ANALYSIS_SHA256", m8["sha256"])
    monkeypatch.setattr(subject, "M7_PREDICTION_COUNT", len(rows))
    config = {
        "schema_version": "post-m8-conditional-risk-config-v1",
        "protocol_version": "post-m8-risk-extension-v1",
        "historical_evidence": {
            "m7_sealed_evaluation_sha256": evaluation["sha256"],
            "m8_analysis_sha256": m8["sha256"],
            "m7_prediction_count": len(rows),
            "historical_decision_threshold": 0.10,
        },
    }
    return config, evaluation, m8


def test_m9_is_deterministic_raw_free_and_detects_composition_reversal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, evaluation, m8 = _fixtures(monkeypatch)

    first, report = subject.analyze_conditional_risk(config, evaluation, m8)
    second, _ = subject.analyze_conditional_risk(config, evaluation, m8)

    assert first == second
    assert "rows" not in report
    assert first["rows_persisted"] is False
    assert first["model_refit_performed"] is False
    assert first["threshold_change_performed"] is False
    assert first["conclusion"]["all_three_raw_outcomes_reverse"] is True
    for outcome in subject.RAW_OUTCOMES:
        assessment = first["simpson_type_assessment"][outcome]
        assert assessment["aggregate_difference"] < 0
        assert assessment["all_within_regime_differences_positive"] is True
        assert assessment["classification"].startswith("SIMPSON_TYPE")


def test_regression_is_conditional_diagnostic_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, evaluation, m8 = _fixtures(monkeypatch)

    analysis, _ = subject.analyze_conditional_risk(config, evaluation, m8)
    regression = analysis["conditional_regression_ols_hc3"]["next_abs_log_return"]

    assert regression["predicted_high_risk_coefficient"] > 0
    assert regression["hc3_standard_error"] >= 0
    assert regression["used_for_classifier_selection_or_tuning"] is False
    assert regression["causal_interpretation_allowed"] is False


def test_m9_rejects_tampered_m7_or_m8_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, evaluation, m8 = _fixtures(monkeypatch)
    tampered_evaluation = deepcopy(evaluation)
    tampered_evaluation["rows"][0]["calibrated_probability"] = 0.99
    with pytest.raises(ValueError, match="M7 evaluation SHA-256 mismatch"):
        subject.analyze_conditional_risk(config, tampered_evaluation, m8)

    tampered_m8 = deepcopy(m8)
    tampered_m8["m7_rerun_performed"] = True
    with pytest.raises(ValueError, match="M8 analysis SHA-256 mismatch"):
        subject.analyze_conditional_risk(config, evaluation, tampered_m8)


def test_m9_rejects_prediction_label_drift_after_valid_rehash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, evaluation, m8 = _fixtures(monkeypatch)
    drifted = deepcopy(evaluation)
    drifted["rows"][0]["predicted_label"] = "NORMAL"
    content = {key: value for key, value in drifted.items() if key != "sha256"}
    drifted["sha256"] = subject._hash(content)
    monkeypatch.setattr(subject, "M7_EVALUATION_SHA256", drifted["sha256"])
    config["historical_evidence"]["m7_sealed_evaluation_sha256"] = drifted["sha256"]
    m8_content = {key: value for key, value in m8.items() if key != "sha256"}
    m8_content["sealed_evaluation_sha256"] = drifted["sha256"]
    m8 = {**m8_content, "sha256": subject._hash(m8_content)}
    monkeypatch.setattr(subject, "M8_ANALYSIS_SHA256", m8["sha256"])
    config["historical_evidence"]["m8_analysis_sha256"] = m8["sha256"]

    with pytest.raises(ValueError, match="historical threshold"):
        subject.analyze_conditional_risk(config, drifted, m8)
