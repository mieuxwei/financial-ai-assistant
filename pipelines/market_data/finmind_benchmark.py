from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

ENDPOINT = "https://api.finmindtrade.com/api/v4/data"
DATASET_ID = "TaiwanStockTotalReturnIndex"
BENCHMARK_ID = "TAIEX"
SCHEMA_VERSION = "finmind-taiex-total-return-v1"


def fetch_taiex_total_return(
    start_date: date,
    end_date: date,
    *,
    client: httpx.Client | None = None,
) -> dict[str, object]:
    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "financial-ai-assistant/0.1 benchmark-audit"},
    )
    try:
        response = active_client.get(
            ENDPOINT,
            params={
                "dataset": DATASET_ID,
                "data_id": BENCHMARK_ID,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            active_client.close()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("FinMind benchmark response did not contain a data list")
    rows = []
    seen_dates = set()
    for raw in payload["data"]:
        if not isinstance(raw, dict):
            raise TypeError("FinMind benchmark row must be an object")
        trading_date = date.fromisoformat(str(raw["date"]))
        price = Decimal(str(raw["price"]))
        if trading_date in seen_dates or price <= 0:
            raise ValueError("FinMind benchmark rows must have unique dates and positive prices")
        seen_dates.add(trading_date)
        rows.append(
            {
                "date": trading_date.isoformat(),
                "price": format(price, "f"),
                "stock_id": str(raw["stock_id"]),
            }
        )
    rows.sort(key=lambda row: row["date"])
    content = {
        "schema_version": SCHEMA_VERSION,
        "endpoint": ENDPOINT,
        "dataset_id": DATASET_ID,
        "benchmark_id": BENCHMARK_ID,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "raw_content_stored": False,
    }
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**content, "sha256": hashlib.sha256(canonical.encode()).hexdigest()}


def write_benchmark_snapshot(path: Path, snapshot: dict[str, object]) -> None:
    payload = (
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(
                f"refusing to overwrite a different benchmark snapshot: {path}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
