import pytest

from pipelines.sentiment.finbert import FinBertModel
from pipelines.sentiment.text import build_sentiment_text, supports_language
from pipelines.sentiment.types import SentimentPrediction


def test_prediction_score_and_label() -> None:
    prediction = SentimentPrediction(0.7, 0.2, 0.1)
    assert prediction.label == "positive"
    assert prediction.score == pytest.approx(0.6)


def test_invalid_probabilities_are_rejected() -> None:
    with pytest.raises(ValueError, match="sum to one"):
        SentimentPrediction(0.4, 0.4, 0.4)


def test_finbert_label_mapping_uses_model_config() -> None:
    mapping = FinBertModel._resolve_label_indices(
        {0: "positive", 1: "negative", 2: "neutral"}
    )
    assert mapping == {"positive": 0, "neutral": 2, "negative": 1}


def test_language_gate_and_text_contract() -> None:
    assert supports_language("en-US", ("en",))
    assert not supports_language("zh-TW", ("en",))
    assert build_sentiment_text("Profit rises", "Profit rises") == "Profit rises"
    assert build_sentiment_text("Profit rises", "Demand improved") == (
        "Profit rises\nDemand improved"
    )
