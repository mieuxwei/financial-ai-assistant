from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path

from pipelines.sentiment.huggingface_classifier import PinnedHuggingFaceSentimentModel
from pipelines.sentiment.lexicon_zh import ChineseFinancialLexiconModel
from pipelines.sentiment.translated_finbert import TranslatedFinBertModel
from research.evaluation.classification_metrics import classification_report

DEFAULT_SAMPLES = Path("research/evaluation/chinese_financial_sentiment_samples.json")
YIYANG_MODEL = "yiyanghkust/finbert-tone-chinese"
YIYANG_REVISION = "e91b1a3af10e1e8c9c03429d3cd7d5e9a1c8000d"
BARDSAI_MODEL = "bardsai/finance-sentiment-zh-base"
BARDSAI_REVISION = "33595d152578da080c6e5c94b60eba15a769107f"
MULTILINGUAL_MODEL = "Kenpache/finbert-multilingual-v2"
MULTILINGUAL_REVISION = "d6a74c217b67aadca64851af2db86514074d25a6"
MODEL_CHOICES = (
    "lexicon",
    "yiyang",
    "bardsai",
    "multilingual-v2",
    "translated-finbert",
)
MIN_ADOPTION_MACRO_F1 = 0.70
MIN_ADOPTION_CLASS_RECALL = 0.60


def build_model(name: str, *, local_files_only: bool):
    if name == "lexicon":
        return ChineseFinancialLexiconModel()
    if name == "yiyang":
        return PinnedHuggingFaceSentimentModel(
            model_id=YIYANG_MODEL,
            revision=YIYANG_REVISION,
            supported_language_prefixes=("zh",),
            label_by_index=("neutral", "positive", "negative"),
            local_files_only=local_files_only,
        )
    if name == "bardsai":
        return PinnedHuggingFaceSentimentModel(
            model_id=BARDSAI_MODEL,
            revision=BARDSAI_REVISION,
            supported_language_prefixes=("zh",),
            local_files_only=local_files_only,
        )
    if name == "multilingual-v2":
        return PinnedHuggingFaceSentimentModel(
            model_id=MULTILINGUAL_MODEL,
            revision=MULTILINGUAL_REVISION,
            supported_language_prefixes=("zh",),
            max_length=192,
            force_fast_tokenizer=True,
            local_files_only=local_files_only,
        )
    if name == "translated-finbert":
        return TranslatedFinBertModel(local_files_only=local_files_only)
    raise ValueError(f"unsupported benchmark model: {name}")


def evaluate_model(
    name: str,
    samples: list[dict[str, str]],
    *,
    local_files_only: bool,
) -> dict[str, object]:
    started = time.perf_counter()
    model = build_model(name, local_files_only=local_files_only)
    load_seconds = time.perf_counter() - started
    texts = [sample["text"] for sample in samples]
    inference_started = time.perf_counter()
    predictions = model.predict_batch(texts)
    inference_seconds = time.perf_counter() - inference_started
    if len(predictions) != len(samples):
        raise ValueError("benchmark model returned an unexpected result count")
    expected = [sample["expected"] for sample in samples]
    predicted = [prediction.label for prediction in predictions]
    translations = getattr(model, "last_translations", [None] * len(samples))
    records = [
        {
            "id": sample["id"],
            "event_type": sample["event_type"],
            "expected": sample["expected"],
            "predicted": prediction.label,
            "positive_prob": round(prediction.positive_prob, 8),
            "neutral_prob": round(prediction.neutral_prob, 8),
            "negative_prob": round(prediction.negative_prob, 8),
            "translation": translation,
        }
        for sample, prediction, translation in zip(
            samples, predictions, translations, strict=True
        )
    ]
    metrics = classification_report(expected, predicted)
    recalls = {
        label: values["recall"] for label, values in metrics["per_class"].items()
    }
    result = {
        "profile": name,
        "model_version": model.model_version,
        "sample_count": len(samples),
        "load_seconds": round(load_seconds, 4),
        "inference_seconds": round(inference_seconds, 4),
        "metrics": metrics,
        "metric_gate": {
            "minimum_macro_f1": MIN_ADOPTION_MACRO_F1,
            "minimum_per_class_recall": MIN_ADOPTION_CLASS_RECALL,
            "passed": metrics["macro_f1"] >= MIN_ADOPTION_MACRO_F1
            and min(recalls.values()) >= MIN_ADOPTION_CLASS_RECALL,
        },
        "errors": [record for record in records if record["expected"] != record["predicted"]],
        "records": records,
    }
    del model
    gc.collect()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark Traditional Chinese financial sentiment approaches"
    )
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--models",
        default=",".join(MODEL_CHOICES),
        help=f"comma-separated profiles: {', '.join(MODEL_CHOICES)}",
    )
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        raise ValueError("Chinese sample file must contain a non-empty list")
    names = [name.strip() for name in args.models.split(",") if name.strip()]
    invalid = set(names) - set(MODEL_CHOICES)
    if invalid:
        raise ValueError(f"invalid model profiles: {sorted(invalid)}")
    report = {
        "dataset": str(args.samples),
        "language": "zh-TW",
        "sample_count": len(samples),
        "results": [
            evaluate_model(name, samples, local_files_only=args.local_files_only)
            for name in names
        ],
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    if args.quiet:
        print(
            json.dumps(
                [
                    {
                        "profile": result["profile"],
                        "model_version": result["model_version"],
                        "accuracy": result["metrics"]["accuracy"],
                        "macro_f1": result["metrics"]["macro_f1"],
                        "metric_gate_passed": result["metric_gate"]["passed"],
                        "errors": len(result["errors"]),
                        "load_seconds": result["load_seconds"],
                        "inference_seconds": result["inference_seconds"],
                    }
                    for result in report["results"]
                ],
                ensure_ascii=False,
            )
        )
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
