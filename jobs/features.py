from __future__ import annotations

import argparse
import json
from datetime import date, time
from pathlib import Path

from backend.app.core.database import SessionLocal
from backend.app.services.features import FeatureDatasetService
from pipelines.features.snapshot import write_feature_dataset
from pipelines.features.types import FeatureConfig


def load_config(path: Path) -> FeatureConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FeatureConfig(
        tickers=tuple(payload["tickers"]),
        start_date=date.fromisoformat(payload["start_date"]),
        end_date=date.fromisoformat(payload["end_date"]),
        market_source=payload["market_source"],
        sentiment_model_version=payload.get("sentiment_model_version"),
        benchmark_ticker=payload.get("benchmark_ticker"),
        market_timezone=payload.get("market_timezone", "Asia/Taipei"),
        market_close_time=time.fromisoformat(payload.get("market_close_time", "13:30:00")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a versioned leakage-safe modeling dataset")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    with SessionLocal() as session:
        result = FeatureDatasetService(session).build(config)
    if args.snapshot:
        write_feature_dataset(args.snapshot, result.dataset)
    print(
        json.dumps(
            {
                "dataset_run_id": result.dataset_run_id,
                "status": result.status,
                "row_count": result.row_count,
                "dataset_sha256": result.dataset_sha256,
                "reused": result.reused,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
