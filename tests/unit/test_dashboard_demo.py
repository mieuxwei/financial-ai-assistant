from __future__ import annotations

from pathlib import Path

from demo.contracts import (
    canonical_dashboard_config_sha256,
    canonical_fixture_sha256,
    load_controlled_fixture,
    load_dashboard_config,
)
from demo.fixture_builder import _synthetic_features
from demo.presentation import (
    band_label,
    event_summary,
    format_percentile,
    format_score,
    sentiment_summary,
)
from pipelines.features.risk_builder import FEATURE_NAMES

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/dashboard_demo.v1.json"


def _assets():
    config = load_dashboard_config(CONFIG_PATH)
    fixture = load_controlled_fixture(ROOT / config.fixture_path)
    return config, fixture


def test_dashboard_config_freezes_public_demo_boundary() -> None:
    config, _ = _assets()

    assert config.modes == ("CONTROLLED_OFFLINE", "LOCAL_API")
    assert config.default_mode == "CONTROLLED_OFFLINE"
    assert set(config.allowed_api_hosts) == {"127.0.0.1", "localhost", "::1"}
    assert config.controlled_data_only is True
    assert config.private_holdings_in_demo is False
    assert config.external_api_calls_in_offline_mode is False
    assert config.automatic_gas_modification is False
    assert config.deploy_in_f11 is False
    assert len(canonical_dashboard_config_sha256(config)) == 64


def test_controlled_fixture_is_synthetic_and_contract_complete() -> None:
    _, fixture = _assets()

    assert fixture.controlled_synthetic_data is True
    assert fixture.actual_market_observation is False
    assert fixture.performance_evaluation is False
    assert fixture.private_or_user_data is False
    assert set(fixture.prediction_request.features) == set(FEATURE_NAMES)
    assert fixture.prediction_request.features == _synthetic_features()
    assert fixture.prediction_response.model_version == "final-ridge-research-model-v1"
    assert len(fixture.prediction_response.artifact_sha256) == 64
    assert fixture.prediction_response.claim_boundary.investment_advice is False
    assert len(canonical_fixture_sha256(fixture)) == 64


def test_fixture_preserves_chinese_abstention_and_event_claim_boundary() -> None:
    _, fixture = _assets()
    chinese, english = fixture.intelligence_items

    assert chinese.language == "zh-TW"
    assert chinese.sentiment.status == "ABSTAIN"
    assert chinese.sentiment.abstention_reason == "CHINESE_SENTIMENT_NOT_VALIDATED"
    assert chinese.sentiment.positive_probability is None
    assert chinese.sentiment.neutral_probability is None
    assert chinese.sentiment.negative_probability is None
    assert chinese.event_intelligence.sentiment_ground_truth is False
    assert chinese.claim_boundary.chinese_sentiment_validated is False
    assert english.language == "en"
    assert english.sentiment.status == "ELIGIBLE_NOT_SCORED"
    assert all(item.generated_summary is None for item in fixture.intelligence_items)
    assert all(item.claim_boundary.llm_generated is False for item in fixture.intelligence_items)


def test_dashboard_presentation_is_explicit_about_unvalidated_outputs() -> None:
    _, fixture = _assets()
    chinese, english = fixture.intelligence_items

    assert format_score("1.423") == "1.42×"
    assert format_percentile(87.459) == "87.5%"
    assert band_label("VERY_HIGH") == "非常高"
    assert "不輸出" in sentiment_summary(chinese)
    assert "尚未執行模型" in sentiment_summary(english)
    assert "非情緒 ground truth" in event_summary(chinese)
