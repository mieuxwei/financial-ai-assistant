from __future__ import annotations

from typing import Any

from pipelines.sentiment.types import LABELS, SentimentPrediction

DEFAULT_MODEL_ID = "ProsusAI/finbert"
DEFAULT_MODEL_REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"


class FinBertDependencyError(RuntimeError):
    """Raised when optional NLP dependencies are unavailable."""


class FinBertModel:
    supported_language_prefixes = ("en",)

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = DEFAULT_MODEL_REVISION,
        max_length: int = 512,
        local_files_only: bool = False,
    ) -> None:
        if not revision:
            raise ValueError("a pinned model revision is required")
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as error:
            raise FinBertDependencyError(
                "install the project nlp extra before running FinBERT inference"
            ) from error

        self.model_version = f"{model_id}@{revision}"
        self.max_length = max_length
        self._torch = torch
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=local_files_only,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=local_files_only,
        )
        self.model.eval()
        self._label_indices = self._resolve_label_indices(self.model.config.id2label)

    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]:
        if not texts:
            return []
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        with self._torch.inference_mode():
            logits = self.model(**encoded).logits
            rows = self._torch.softmax(logits, dim=-1).cpu().tolist()
        return [
            SentimentPrediction(
                positive_prob=row[self._label_indices["positive"]],
                neutral_prob=row[self._label_indices["neutral"]],
                negative_prob=row[self._label_indices["negative"]],
            )
            for row in rows
        ]

    @staticmethod
    def _resolve_label_indices(id2label: dict[Any, str]) -> dict[str, int]:
        normalized = {str(label).casefold(): int(index) for index, label in id2label.items()}
        missing = set(LABELS) - normalized.keys()
        if missing:
            raise ValueError(f"FinBERT label mapping is missing: {sorted(missing)}")
        return {label: normalized[label] for label in LABELS}

