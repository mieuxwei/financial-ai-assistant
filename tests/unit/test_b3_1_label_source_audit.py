import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/b3_1_chinese_sentiment_label_sources.v1.json"
REPORT = ROOT / "research/evaluation/b3_1_chinese_sentiment_label_source_audit.md"


def _load() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_b3_1_is_bounded_to_three_primary_candidates() -> None:
    payload = _load()
    candidates = payload["candidates"]

    assert len(candidates) == 3
    assert {item["candidate_id"] for item in candidates} == {
        "cfsc-absa",
        "multilingual-financial-sentiment-zh",
        "stocksentcn",
    }
    assert all(item["final_classification"] == "HOLD" for item in candidates)


def test_b3_1_preserves_research_and_safety_boundaries() -> None:
    payload = _load()
    scope = payload["scope"]
    decision = payload["decision"]

    assert scope["eland_used"] is False
    assert scope["bulk_download_performed"] is False
    assert scope["sentiment_model_trained"] is False
    assert scope["manual_labels_created"] is False
    assert scope["manual_label_review_performed"] is False
    assert decision["gating_answer"] == "NO"
    assert decision["b3_2_created"] is False
    assert decision["next_executable_unit"] == "B4_VALIDATION_ABSTENTION_DECISION"
    assert decision["b4_gate_unchanged"] == {
        "macro_f1_minimum": 0.7,
        "per_required_class_recall_minimum": 0.6,
    }


def test_b3_1_report_contains_required_decisions() -> None:
    report = REPORT.read_text(encoding="utf-8")

    for source in ("CFSC-ABSA", "Multilingual Financial Sentiment", "StockSentCN"):
        assert source.lower() in report.lower()
    assert "**NO**" in report
    assert "B3.2 is not created" in report
    assert "No sentiment model was trained" in report
