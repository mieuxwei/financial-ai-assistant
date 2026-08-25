from typing import Protocol

from pipelines.sentiment.types import SentimentPrediction


class SentimentModel(Protocol):
    model_version: str
    supported_language_prefixes: tuple[str, ...]

    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]: ...

