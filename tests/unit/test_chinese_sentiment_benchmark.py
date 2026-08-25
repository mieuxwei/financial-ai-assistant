import pytest

from pipelines.sentiment.lexicon_zh import ChineseFinancialLexiconModel
from research.evaluation.classification_metrics import classification_report


def test_lexicon_baseline_is_transparent_for_explicit_terms() -> None:
    model = ChineseFinancialLexiconModel()
    predictions = model.predict_batch(
        [
            "公司營收創新高並上調展望。",
            "公司虧損擴大並下修展望。",
            "公司將召開股東常會。",
        ]
    )
    assert [prediction.label for prediction in predictions] == [
        "positive",
        "negative",
        "neutral",
    ]


def test_classification_report_computes_macro_metrics() -> None:
    report = classification_report(
        ["positive", "neutral", "negative"],
        ["positive", "negative", "negative"],
    )
    assert report["accuracy"] == pytest.approx(2 / 3)
    assert report["macro_f1"] == pytest.approx((1.0 + 0.0 + 2 / 3) / 3)
    assert report["confusion"] == {
        "positive->positive": 1,
        "neutral->negative": 1,
        "negative->negative": 1,
    }
