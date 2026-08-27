from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from jobs.financial_nlp_intelligence import run
from pipelines.intelligence.financial_nlp import (
    assemble_intelligence_item,
    load_financial_nlp_intelligence_config,
    verify_historical_evidence,
)
from pipelines.news.types import NewsItem, TickerMatch
from pipelines.sentiment.types import SentimentPrediction

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/financial_nlp_intelligence.v1.json"
TAIPEI = ZoneInfo("Asia/Taipei")


def _config():
    return load_financial_nlp_intelligence_config(CONFIG_PATH)


def _item(*, language: str, title: str, summary: str | None = None) -> NewsItem:
    return NewsItem(
        title=title,
        summary=summary,
        published_at=datetime(2024, 1, 2, 9, tzinfo=TAIPEI),
        source="test_source",
        source_type="test_type",
        url="https://example.invalid/item",
        language=language,
        external_id=f"test-{language}-{title}",
    )


def test_config_freezes_supported_model_exclusion_and_zero_manual_boundary() -> None:
    config = _config()

    assert config.english_model_version.endswith(
        "@4556d13015211d73dccd3fdd39d39232506f3e43"
    )
    assert config.taiwan_sentiment["status"] == "UNSUPPORTED_ABSTAIN"
    assert config.eland["status"] == "HOLD_EXCLUDED_FROM_ACTIVE_MODELING"
    assert config.eland["allowed_role"] == "HISTORICAL_REJECTION_EVIDENCE_ONLY"
    assert config.manual_annotation_allowed is False
    assert config.manual_label_review_allowed is False
    assert config.track_a_dependency_on_nlp_success is False


def test_historical_evidence_hashes_are_verified() -> None:
    results = verify_historical_evidence(_config(), repository_root=ROOT)

    assert len(results) == 7
    assert all(row["passed"] for row in results)


def test_english_is_eligible_but_not_fabricated_when_model_does_not_run() -> None:
    record = assemble_intelligence_item(
        _config(), _item(language="en", title="Company reports results"), []
    )

    assert record["sentiment"]["status"] == "ELIGIBLE_NOT_SCORED"
    assert record["sentiment"]["label"] is None
    assert record["sentiment"]["positive_probability"] is None
    assert record["sentiment"]["neutral_probability"] is None
    assert record["sentiment"]["negative_probability"] is None
    assert record["sentiment"]["score"] is None
    assert record["generated_summary"] is None


def test_english_prediction_requires_exact_pinned_model_revision() -> None:
    config = _config()
    prediction = SentimentPrediction(0.7, 0.2, 0.1)
    item = _item(language="en-US", title="Company wins an order")
    record = assemble_intelligence_item(
        config,
        item,
        [],
        sentiment_prediction=prediction,
        sentiment_model_version=config.english_model_version,
    )

    assert record["sentiment"]["status"] == "SCORED"
    assert record["sentiment"]["label"] == "positive"
    assert record["sentiment"]["score"] == pytest.approx(0.6)
    with pytest.raises(ValueError, match="pinned FinBERT"):
        assemble_intelligence_item(
            config,
            item,
            [],
            sentiment_prediction=prediction,
            sentiment_model_version="ProsusAI/finbert@floating-main",
        )


def test_chinese_abstains_while_event_proxy_stays_separate() -> None:
    item = _item(language="zh-TW", title="公司公告月營收成長並取得重大訂單")
    record = assemble_intelligence_item(
        _config(), item, [TickerMatch("2330", 1.0, "official_company_code")]
    )

    assert record["sentiment"]["status"] == "ABSTAIN"
    assert record["sentiment"]["abstention_reason"] == "CHINESE_SENTIMENT_NOT_VALIDATED"
    assert record["sentiment"]["positive_probability"] is None
    assert record["event_intelligence"]["status"] == "SIGNAL"
    assert record["event_intelligence"]["normalized_event_type"] == "REVENUE"
    assert record["event_intelligence"]["impact_proxy"] == "POSITIVE"
    assert record["event_intelligence"]["sentiment_ground_truth"] is False
    assert record["claim_boundary"]["event_proxy_is_sentiment_ground_truth"] is False


def test_chinese_prediction_is_rejected_and_no_rule_match_abstains() -> None:
    config = _config()
    item = _item(language="zh-TW", title="依規定補充說明相關資訊")
    record = assemble_intelligence_item(config, item, [])

    assert record["sentiment"]["status"] == "ABSTAIN"
    assert record["event_intelligence"]["status"] == "ABSTAIN"
    assert record["event_intelligence"]["abstention_reason"] == "NO_RULE_MATCH"
    with pytest.raises(ValueError, match="only accepted for supported English"):
        assemble_intelligence_item(
            config,
            item,
            [],
            sentiment_prediction=SentimentPrediction(0.3, 0.4, 0.3),
            sentiment_model_version=config.english_model_version,
        )


def test_f8_audit_is_deterministic_and_does_not_persist_fixture_rows(tmp_path: Path) -> None:
    analysis_path = ROOT / ".tools/evaluation/f8-financial-nlp-intelligence-v1/analysis.json"
    report_path = ROOT / "artifacts/f8-financial-nlp-intelligence-report.json"
    first = run(CONFIG_PATH, analysis_path, report_path)
    second = run(CONFIG_PATH, analysis_path, report_path)

    assert first == second
    assert first["passed"] is True
    assert first["external_api_called"] is False
    assert first["model_inference_performed"] is False
    assert first["model_training_performed"] is False
    analysis_text = analysis_path.read_text(encoding="utf-8")
    assert '"fixture_rows_persisted": false' in analysis_text
    assert "公司公告" not in analysis_text
