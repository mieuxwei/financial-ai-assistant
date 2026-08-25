import hashlib
import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.repositories.market_data import MarketDataRepository

SNAPSHOT_SCHEMA_VERSION = "market-prices-v1"


def build_market_snapshot(
    session: Session,
    *,
    tickers: list[str],
    start_date: date,
    end_date: date,
    source: str,
) -> dict[str, object]:
    rows = MarketDataRepository(session).list_bars(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
    data = [
        {
            "ticker": row.ticker,
            "trading_date": row.trading_date.isoformat(),
            "open": format(row.open, "f"),
            "high": format(row.high, "f"),
            "low": format(row.low, "f"),
            "close": format(row.close, "f"),
            "adjusted_close": format(row.adjusted_close, "f"),
            "volume": row.volume,
            "source": row.source,
        }
        for row in rows
    ]
    snapshot_content = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "source": source,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "tickers": sorted(tickers),
        "rows": data,
    }
    canonical = json.dumps(
        snapshot_content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        **snapshot_content,
        "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def write_market_snapshot(path: Path, snapshot: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
