from __future__ import annotations

from math import isfinite
from typing import TypedDict

MAX_DEMO_HOLDINGS = 5
MAX_DEMO_SHARES = 10_000_000.0
MAX_DEMO_AVERAGE_COST = 1_000_000.0

FROZEN_UNIVERSE: dict[str, str] = {
    "0050": "元大台灣50",
    "1301": "台塑",
    "1303": "南亞",
    "2308": "台達電",
    "2317": "鴻海",
    "2330": "台積電",
    "2412": "中華電",
    "2454": "聯發科",
    "2881": "富邦金",
    "2882": "國泰金",
}


class BrowserDemoHolding(TypedDict):
    ticker: str
    company: str
    shares: float
    average_cost: float


def build_holding(ticker: str, shares: float, average_cost: float) -> BrowserDemoHolding:
    normalized_ticker = str(ticker).strip()
    if normalized_ticker not in FROZEN_UNIVERSE:
        raise ValueError("股票代號不在 frozen 10-ticker universe。")
    normalized_shares = _positive_finite(shares, MAX_DEMO_SHARES, "持有股數")
    normalized_cost = _positive_finite(average_cost, MAX_DEMO_AVERAGE_COST, "平均成本")
    return {
        "ticker": normalized_ticker,
        "company": FROZEN_UNIVERSE[normalized_ticker],
        "shares": normalized_shares,
        "average_cost": normalized_cost,
    }


def upsert_holding(
    holdings: list[BrowserDemoHolding],
    holding: BrowserDemoHolding,
) -> list[BrowserDemoHolding]:
    updated = [dict(item) for item in holdings]
    for index, existing in enumerate(updated):
        if existing["ticker"] == holding["ticker"]:
            updated[index] = dict(holding)
            return updated
    if len(updated) >= MAX_DEMO_HOLDINGS:
        raise ValueError(f"Web Demo 最多只能加入 {MAX_DEMO_HOLDINGS} 檔持股。")
    updated.append(dict(holding))
    return updated


def delete_holding(holdings: list[BrowserDemoHolding], ticker: str) -> list[BrowserDemoHolding]:
    return [dict(item) for item in holdings if item["ticker"] != ticker]


def _positive_finite(value: float, ceiling: float, label: str) -> float:
    number = float(value)
    if not isfinite(number) or number <= 0 or number > ceiling:
        raise ValueError(f"{label}必須大於 0，且不得超過 {ceiling:,.0f}。")
    return number
