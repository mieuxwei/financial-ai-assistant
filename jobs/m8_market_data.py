from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from backend.app.core.database import SessionLocal
from backend.app.services.market_data import MarketDataIngestionService
from jobs.market_data import parse_config
from pipelines.market_data.yahoo import YahooFinanceProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest the M8 event universe one ticker at a time with explicit failures"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    requests = parse_config(args.config, args.start, args.end)
    succeeded = []
    failed = []
    records_fetched = 0
    records_upserted = 0
    with YahooFinanceProvider() as provider:
        for request in requests:
            try:
                with SessionLocal() as session:
                    result = MarketDataIngestionService(session, provider).ingest([request])
                succeeded.append(request.ticker)
                records_fetched += result.records_fetched
                records_upserted += result.records_upserted
            except Exception as error:
                failed.append(
                    {
                        "ticker": request.ticker,
                        "error_code": type(error).__name__,
                    }
                )
    print(
        json.dumps(
            {
                "requested_ticker_count": len(requests),
                "succeeded_ticker_count": len(succeeded),
                "failed_ticker_count": len(failed),
                "records_fetched": records_fetched,
                "records_upserted": records_upserted,
                "failure_codes": dict(
                    sorted(Counter(item["error_code"] for item in failed).items())
                ),
                "failed": failed,
                "contains_secrets": False,
                "contains_private_holdings": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if succeeded else 2


if __name__ == "__main__":
    raise SystemExit(main())
