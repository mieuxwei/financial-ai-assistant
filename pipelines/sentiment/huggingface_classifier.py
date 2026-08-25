from __future__ import annotations

from typing import Any

from pipelines.sentiment.finbert import FinBertDependencyError
from pipelines.sentiment.types import LABELS, SentimentPrediction


class PinnedHuggingFaceSentimentModel:
    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        supported_language_prefixes: tuple[str, ...],
        label_by_index: tuple[str, ...] | None = None,
        max_length: int = 256,
        force_fast_tokenizer: bool = False,
        local_files_only: bool = False,
    ) -> None:
        if not revision:
            raise ValueError("a pinned model revision is required")
        try:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                PreTrainedTokenizerFast,
            )
        except ImportError as error:
            raise FinBertDependencyError(
                "install the project nlp extra before running model inference"
            ) from error

        self.model_version = f"{model_id}@{revision}"
        self.supported_language_prefixes = supported_language_prefixes
        self.max_length = max_length
        self._torch = torch
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        if force_fast_tokenizer:
            from huggingface_hub import hf_hub_download

            tokenizer_file = hf_hub_download(
                repo_id=model_id,
                filename="tokenizer.json",
                revision=revision,
                local_files_only=local_files_only,
            )
            self.tokenizer = PreTrainedTokenizerFast(
                tokenizer_file=tokenizer_file,
                bos_token="<bos>",
                eos_token="<eos>",
                unk_token="<unk>",
                sep_token="<eos>",
                pad_token="<pad>",
                cls_token="<bos>",
                mask_token="<mask>",
                model_max_length=8192,
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id, revision=revision, local_files_only=local_files_only
            )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        self.model.eval()
        self._label_indices = self._resolve_label_indices(
            self.model.config.id2label, label_by_index
        )

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
    def _resolve_label_indices(
        id2label: dict[Any, str], label_by_index: tuple[str, ...] | None
    ) -> dict[str, int]:
        if label_by_index is not None:
            normalized = {
                label.casefold(): index for index, label in enumerate(label_by_index)
            }
        else:
            normalized = {
                str(label).casefold(): int(index) for index, label in id2label.items()
            }
        missing = set(LABELS) - normalized.keys()
        if missing:
            raise ValueError(f"sentiment label mapping is missing: {sorted(missing)}")
        return {label: normalized[label] for label in LABELS}
