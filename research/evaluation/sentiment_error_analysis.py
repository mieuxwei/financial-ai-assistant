from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from pipelines.sentiment.finbert import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    FinBertModel,
)

DEFAULT_SAMPLES = Path("research/evaluation/finbert_manual_samples.json")


def evaluate(samples: list[dict[str, str]], model: FinBertModel) -> dict[str, object]:
    predictions = model.predict_batch([sample["text"] for sample in samples])
    records = []
    confusion: Counter[str] = Counter()
    correct = 0
    for sample, prediction in zip(samples, predictions, strict=True):
        expected = sample["expected"]
        predicted = prediction.label
        correct += expected == predicted
        confusion[f"{expected}->{predicted}"] += 1
        records.append(
            {
                "id": sample["id"],
                "expected": expected,
                "predicted": predicted,
                "positive_prob": round(prediction.positive_prob, 8),
                "neutral_prob": round(prediction.neutral_prob, 8),
                "negative_prob": round(prediction.negative_prob, 8),
                "sentiment_score": round(prediction.score, 8),
            }
        )
    return {
        "model_version": model.model_version,
        "sample_count": len(samples),
        "accuracy": correct / len(samples),
        "confusion": dict(sorted(confusion.items())),
        "records": records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate FinBERT on manual samples")
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        raise ValueError("manual sample file must contain a non-empty list")
    report = evaluate(
        samples,
        FinBertModel(
            model_id=args.model,
            revision=args.revision,
            local_files_only=args.local_files_only,
        ),
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
