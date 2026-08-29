from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pipelines.news.twmd_major_events import TwmdMajorEventProvider
from research.evaluation.twmd_pro_reaudit import load_api_key

DEFAULT_CONFIG = Path("research/configs/b4_twmd_historical_backfill.v1.json")


class BackfillConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backfill_version: str
    source_contract: str
    date_from: date
    date_to: date
    tickers: list[str] = Field(min_length=1)
    windowing: str
    maximum_window_days: int = Field(le=31)
    request_limit: int = Field(le=100)
    maximum_workers: int = Field(ge=1, le=4)
    private_output: Path
    raw_or_normalized_subject_publication_allowed: bool
    redistribution_allowed: bool
    purpose: str


def load_config(path: Path = DEFAULT_CONFIG) -> BackfillConfig:
    config = BackfillConfig.model_validate_json(path.read_text(encoding="utf-8"))
    if config.raw_or_normalized_subject_publication_allowed or config.redistribution_allowed:
        raise ValueError("TWMD licensed subjects must remain private")
    return config


def month_windows(start: date, end: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        if cursor.month == 12:
            next_month = date(cursor.year + 1, 1, 1)
        else:
            next_month = date(cursor.year, cursor.month + 1, 1)
        window_end = min(end, date.fromordinal(next_month.toordinal() - 1))
        windows.append((cursor, window_end))
        cursor = next_month
    return windows


def _batch_path(root: Path, ticker: str, start: date) -> Path:
    return root / "private_batches" / ticker / f"{start:%Y-%m}.json"


def _fetch_one(
    api_key: str,
    config: BackfillConfig,
    ticker: str,
    start: date,
    end: date,
) -> dict[str, object]:
    path = _batch_path(config.private_output, ticker, start)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {"ticker": ticker, "date_from": start.isoformat(), "cache_hit": True, **payload}
    with TwmdMajorEventProvider(api_key=api_key) as provider:
        batch = provider.fetch(
            ticker=ticker,
            date_from=start,
            date_to=end,
            limit=config.request_limit,
        )
    payload = {
        "date_to": end.isoformat(),
        "events": [
            {
                **asdict(event),
                "event_date": event.event_date.isoformat(),
                "publication_timestamp": event.publication_timestamp.isoformat(),
            }
            for event in batch.events
        ],
        "response_sha256": batch.response_sha256,
        "duplicate_count": batch.duplicate_count,
        "known_gaps": list(batch.known_gaps),
        "warnings": list(batch.warnings),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"ticker": ticker, "date_from": start.isoformat(), "cache_hit": False, **payload}


def run_backfill(config: BackfillConfig) -> dict[str, object]:
    key = load_api_key("TWMD_API_KEY")
    requests = [
        (ticker, start, end)
        for ticker in config.tickers
        for start, end in month_windows(config.date_from, config.date_to)
    ]
    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=config.maximum_workers) as executor:
        futures = {
            executor.submit(_fetch_one, key, config, ticker, start, end): (ticker, start)
            for ticker, start, end in requests
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (str(item["ticker"]), str(item["date_from"])))
    events = [event for result in results for event in result["events"]]
    manifest = {
        "backfill_version": config.backfill_version,
        "source_contract": config.source_contract,
        "date_from": config.date_from.isoformat(),
        "date_to": config.date_to.isoformat(),
        "tickers": config.tickers,
        "request_count": len(results),
        "cache_hit_count": sum(bool(item["cache_hit"]) for item in results),
        "event_count": len(events),
        "zero_row_batch_count": sum(not item["events"] for item in results),
        "provider_duplicate_count": sum(int(item["duplicate_count"]) for item in results),
        "event_count_by_ticker": {
            ticker: sum(event["ticker"] == ticker for event in events)
            for ticker in config.tickers
        },
        "event_count_by_year": {
            str(year): sum(str(event["event_date"]).startswith(f"{year}-") for event in events)
            for year in range(config.date_from.year, config.date_to.year + 1)
        },
        "private_subjects_present": bool(events),
        "public_redistribution_allowed": False,
    }
    manifest_path = config.private_output / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Private bounded TWMD backfill for B4")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run_backfill(load_config(args.config))
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
