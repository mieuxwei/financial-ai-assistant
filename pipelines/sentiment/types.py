from dataclasses import dataclass

LABELS = ("positive", "neutral", "negative")


@dataclass(frozen=True)
class SentimentPrediction:
    positive_prob: float
    neutral_prob: float
    negative_prob: float

    def __post_init__(self) -> None:
        probabilities = (self.positive_prob, self.neutral_prob, self.negative_prob)
        if any(value < 0 or value > 1 for value in probabilities):
            raise ValueError("sentiment probabilities must be between zero and one")
        if abs(sum(probabilities) - 1.0) > 1e-5:
            raise ValueError("sentiment probabilities must sum to one")

    @property
    def score(self) -> float:
        return self.positive_prob - self.negative_prob

    @property
    def label(self) -> str:
        values = {
            "positive": self.positive_prob,
            "neutral": self.neutral_prob,
            "negative": self.negative_prob,
        }
        return max(values, key=values.__getitem__)

