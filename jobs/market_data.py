from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from backend.app.core.database import SessionLocal
from backend.app.services.market_data import MarketDataIngestionService
from pipelines.market_data.snapshot import build_market_snapshot, write_market_snapshot
from pipelines.market_data.types import MarketDataRequest
from pipelines.market_data.yahoo import YahooFinanceProvider


def parse_config(path: Path, start_date: date, end_date: date) -> list[MarketDataRequest]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    instruments = payload.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        raise ValueError("config must contain a non-empty instruments list")
    return [
        MarketDataRequest(
            ticker=item["ticker"],
            provider_symbol=item["provider_symbol"],
            start_date=start_date,
            end_date=end_date,
        )
        for item in instruments
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest historical daily OHLCV")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--snapshot", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    requests = parse_config(args.config, args.start, args.end)
    with SessionLocal() as session, YahooFinanceProvider() as provider:
        result = MarketDataIngestionService(session, provider).ingest(requests)
        if args.snapshot:
            snapshot = build_market_snapshot(
                session,
                tickers=[request.ticker for request in requests],
                start_date=args.start,
                end_date=args.end,
                source=provider.name,
            )
            write_market_snapshot(args.snapshot, snapshot)
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "status": result.status,
                "records_fetched": result.records_fetched,
                "records_upserted": result.records_upserted,
                "quality_report": result.quality_report,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
