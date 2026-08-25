import math

from pipelines.sentiment.types import SentimentPrediction

POSITIVE_TERMS = (
    "創新高",
    "優於預期",
    "超越預期",
    "上調",
    "調升",
    "成長",
    "增加",
    "改善",
    "獲利",
    "盈餘",
    "轉虧為盈",
    "重大訂單",
    "需求強勁",
    "提前償債",
    "提高股利",
)
NEGATIVE_TERMS = (
    "虧損",
    "低於預期",
    "不如預期",
    "下修",
    "調降",
    "衰退",
    "下滑",
    "減少",
    "惡化",
    "停工",
    "裁員",
    "罰款",
    "減損",
    "違約",
    "流失",
    "需求疲弱",
)
NEGATIONS = ("未", "沒有", "並未", "不會", "無")


class ChineseFinancialLexiconModel:
    model_version = "chinese-financial-lexicon@v1"
    supported_language_prefixes = ("zh",)

    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]:
        return [self._predict(text) for text in texts]

    @staticmethod
    def _predict(text: str) -> SentimentPrediction:
        positive = _score_terms(text, POSITIVE_TERMS)
        negative = _score_terms(text, NEGATIVE_TERMS)
        if positive == negative:
            logits = (positive, positive + 1.0, negative)
        else:
            logits = (positive, 0.0, negative)
        probabilities = _softmax(logits)
        return SentimentPrediction(
            positive_prob=probabilities[0],
            neutral_prob=probabilities[1],
            negative_prob=probabilities[2],
        )


def _score_terms(text: str, terms: tuple[str, ...]) -> float:
    score = 0.0
    for term in terms:
        start = text.find(term)
        while start >= 0:
            prefix = text[max(0, start - 2) : start]
            score += -1.0 if any(prefix.endswith(negation) for negation in NEGATIONS) else 1.0
            start = text.find(term, start + len(term))
    return score


def _softmax(values: tuple[float, float, float]) -> tuple[float, float, float]:
    maximum = max(values)
    exponents = tuple(math.exp(value - maximum) for value in values)
    total = sum(exponents)
    return tuple(value / total for value in exponents)
