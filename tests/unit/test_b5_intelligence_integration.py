from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from pipelines.intelligence.b5_integration import (
    assemble_b5_intelligence,
    load_b5_intelligence_config,
)

CONFIG = Path("research/configs/b5_nlp_intelligence_integration.v1.json")
TAIPEI = ZoneInfo("Asia/Taipei")


def _assemble(**metadata: object) -> dict[str, object]:
    return assemble_b5_intelligence(
        load_b5_intelligence_config(CONFIG),
        source="twmd_major_events",
        source_type="LICENSED_EVENT_METADATA",
        published_at=datetime(2025, 6, 2, 18, tzinfo=TAIPEI),
        language="zh-TW",
        metadata=metadata,
        requested_cutoff=datetime(2025, 6, 3, 9, tzinfo=TAIPEI),
    )


def test_chinese_sentiment_and_direction_always_abstain() -> None:
    record = _assemble(
        event_class="重大契約",
        event_confidence=0.9,
        rule_version="mops_taxonomy_v1",
        b5_reaction_magnitude_score=0.013,
        b5_historical_percentile=85.0,
        b5_signal_available_at="2025-06-02T18:01:00+08:00",
    )
    sentiment = record["linguistic_sentiment"]
    assert sentiment == {
        "status": "ABSTAIN",
        "maturity": "ABSTAIN",
        "polarity": None,
        "positive_probability": None,
        "neutral_probability": None,
        "negative_probability": None,
        "reason": "CHINESE_SENTIMENT_NOT_VALIDATED",
    }
    reaction = record["market_reaction"]
    assert reaction["maturity"] == "AUTOMATED_SIGNAL_ONLY"
    assert reaction["communication_band"] == "HIGH"
    assert reaction["direction"] is None
    assert reaction["direction_status"] == "ABSTAIN_DIRECTION_NOT_SUPPORTED"


def test_event_class_and_media_tone_never_populate_sentiment() -> None:
    record = _assemble(
        event_class="重大利多",
        event_confidence=1.0,
        rule_version="fixture",
    )
    assert record["event_classification"]["event_class"] == "重大利多"
    assert record["event_classification"]["sentiment_ground_truth"] is False
    assert record["media_tone"]["tone"] is None
    assert record["linguistic_sentiment"]["polarity"] is None


def test_missing_or_future_availability_timestamp_fails_safe() -> None:
    missing = _assemble(b5_reaction_magnitude_score=0.02, b5_historical_percentile=99)
    future = _assemble(
        b5_reaction_magnitude_score=0.02,
        b5_historical_percentile=99,
        b5_signal_available_at="2025-06-04T00:00:00+08:00",
    )
    assert missing["market_reaction"]["reaction_magnitude_score"] is None
    assert future["market_reaction"]["status"] == "ABSTAIN_SIGNAL_NOT_AVAILABLE_AT_CUTOFF"
    with pytest.raises(ValueError, match="timezone-aware"):
        assemble_b5_intelligence(
            load_b5_intelligence_config(CONFIG),
            source="twmd_major_events",
            source_type="LICENSED_EVENT_METADATA",
            published_at=datetime(2025, 6, 2, 18),
            language="zh-TW",
            metadata={},
            requested_cutoff=None,
        )


def test_contract_has_lineage_and_no_private_or_trading_copy() -> None:
    record = _assemble(private_raw_payload="must-not-leak", subject="licensed-title")
    rendered = str(record)
    assert "must-not-leak" not in rendered
    assert "licensed-title" not in rendered
    assert len(record["lineage"]["b5_config_sha256"]) == 64
    assert record["representation"]["used_for_market_reaction_prediction"] is False
    for prohibited in ("買進", "賣出", "buy", "sell"):
        assert prohibited not in rendered.casefold()
