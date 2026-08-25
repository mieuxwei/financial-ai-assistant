from __future__ import annotations

import argparse
import json

from backend.app.core.database import SessionLocal
from backend.app.services.sentiment import SentimentInferenceService
from pipelines.sentiment.finbert import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    FinBertModel,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run pinned FinBERT sentiment inference")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model = FinBertModel(
        model_id=args.model,
        revision=args.revision,
        local_files_only=args.local_files_only,
    )
    with SessionLocal() as session:
        result = SentimentInferenceService(
            session, model, batch_size=args.batch_size
        ).run()
    print(json.dumps(result.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
