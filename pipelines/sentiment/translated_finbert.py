from __future__ import annotations

from pipelines.sentiment.finbert import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    FinBertDependencyError,
    FinBertModel,
)
from pipelines.sentiment.types import SentimentPrediction

DEFAULT_TRANSLATION_MODEL_ID = "Helsinki-NLP/opus-mt-zh-en"
DEFAULT_TRANSLATION_REVISION = "cf109095479db38d6df799875e34039d4938aaa6"


class TranslatedFinBertModel:
    supported_language_prefixes = ("zh",)

    def __init__(
        self,
        *,
        translation_model_id: str = DEFAULT_TRANSLATION_MODEL_ID,
        translation_revision: str = DEFAULT_TRANSLATION_REVISION,
        local_files_only: bool = False,
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise FinBertDependencyError(
                "install the project nlp extra before running translation"
            ) from error
        self._torch = torch
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self.translation_tokenizer = AutoTokenizer.from_pretrained(
            translation_model_id,
            revision=translation_revision,
            local_files_only=local_files_only,
        )
        self.translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            translation_model_id,
            revision=translation_revision,
            local_files_only=local_files_only,
        )
        self.translation_model.eval()
        self.finbert = FinBertModel(
            model_id=DEFAULT_MODEL_ID,
            revision=DEFAULT_MODEL_REVISION,
            local_files_only=local_files_only,
        )
        self.model_version = (
            f"translate:{translation_model_id}@{translation_revision}"
            f"|sentiment:{self.finbert.model_version}"
        )
        self.last_translations: list[str] = []

    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]:
        if not texts:
            self.last_translations = []
            return []
        encoded = self.translation_tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        with self._torch.inference_mode():
            generated = self.translation_model.generate(
                **encoded,
                do_sample=False,
                num_beams=1,
                max_new_tokens=256,
            )
        self.last_translations = self.translation_tokenizer.batch_decode(
            generated, skip_special_tokens=True
        )
        return self.finbert.predict_batch(self.last_translations)
