"""Bounded, read-only F11B-2A official-source parity audit.

The live collection mode stores normalized source rows only below ``.tools``.
Tracked outputs contain derived statistics and decisions, never raw payloads.
This module is an audit adapter; it is not a production market-data provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from pipelines.features.risk_builder import (
    FEATURE_NAMES,
    _calculate_features,
    load_risk_feature_config,
)

ROOT = Path(__file__).resolve().parents[2]
MARKET_CONFIG = ROOT / "research/configs/risk_market_dataset.v1.json"
FEATURE_CONFIG = ROOT / "research/configs/risk_features.v1.json"
HISTORICAL_DATASET = ROOT / ".tools/datasets/risk-market-dataset-v1/dataset.json"
CACHE_DIR = ROOT / ".tools/audits/f11b-official-current-market-parity-v1"

TWSE_CURRENT_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TWSE_MONTH_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
TWSE_ACTION_URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"
TWSE_TOTAL_RETURN_URL = "https://openapi.twse.com.tw/v1/indicesReport/MFI94U"
TPEX_CURRENT_URL = (
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
)
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

RAW_FIELDS = ("open", "high", "low", "close", "volume")
RAW_ONLY_FEATURES = {
    "overnight_gap_log_1",
    "volume_log_change_1p_1",
    "volume_zscore_20",
    "zero_volume_flag",
    "high_low_log_range_1",
    "atr_14_normalized",
    "parkinson_mean_5",
}
BENCHMARK_ONLY_FEATURES = {
    "benchmark_return_log_1",
    "benchmark_return_log_20",
    "benchmark_volatility_log_return_20",
    "benchmark_drawdown_20",
}


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def roc_date(value: str) -> str:
    """Convert compact or slash-separated ROC dates to ISO dates."""
    clean = value.strip().replace("/", "")
    if len(clean) != 7 or not clean.isdigit():
        raise ValueError(f"unsupported ROC date: {value!r}")
    return f"{int(clean[:3]) + 1911:04d}-{clean[3:5]}-{clean[5:7]}"


def decimal_text(value: object) -> str:
    clean = str(value).strip().replace(",", "")
    if clean in {"", "--", "---", "-"}:
        raise ValueError("missing numeric field")
    return format(Decimal(clean), "f")


def normalize_twse_month(payload: dict[str, Any], ticker: str) -> list[dict[str, object]]:
    fields = payload.get("fields")
    rows = payload.get("data")
    required_prefix = [
        "日期",
        "成交股數",
        "成交金額",
        "開盤價",
        "最高價",
        "最低價",
        "收盤價",
        "漲跌價差",
        "成交筆數",
    ]
    if (
        payload.get("stat") != "OK"
        or not isinstance(fields, list)
        or fields[: len(required_prefix)] != required_prefix
        or not isinstance(rows, list)
    ):
        raise ValueError("TWSE monthly response did not match the frozen audit schema")
    normalized = []
    for row in rows:
        if not isinstance(row, list) or len(row) < len(required_prefix):
            raise ValueError("TWSE monthly row length mismatch")
        normalized.append(
            {
                "ticker": ticker,
                "trading_date": roc_date(str(row[0])),
                "open": decimal_text(row[3]),
                "high": decimal_text(row[4]),
                "low": decimal_text(row[5]),
                "close": decimal_text(row[6]),
                "volume": int(str(row[1]).replace(",", "")),
                "source": "TWSE_STOCK_DAY",
            }
        )
    return normalized


def parse_twse_current(rows: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for row in rows:
        ticker = str(row.get("Code", "")).strip()
        if not ticker:
            continue
        try:
            output[ticker] = {
                "ticker": ticker,
                "name": str(row["Name"]),
                "trading_date": roc_date(str(row["Date"])),
                "open": decimal_text(row["OpeningPrice"]),
                "high": decimal_text(row["HighestPrice"]),
                "low": decimal_text(row["LowestPrice"]),
                "close": decimal_text(row["ClosingPrice"]),
                "volume": int(str(row["TradeVolume"]).replace(",", "")),
                "source": "TWSE_STOCK_DAY_ALL",
            }
        except (KeyError, ValueError):
            continue
    return output


def compare_numeric_rows(
    historical: list[dict[str, object]], official: list[dict[str, object]]
) -> dict[str, object]:
    historical_by_date = {str(row["trading_date"]): row for row in historical}
    official_by_date = {str(row["trading_date"]): row for row in official}
    common = sorted(historical_by_date.keys() & official_by_date.keys())
    fields: dict[str, dict[str, object]] = {}
    for field in RAW_FIELDS:
        abs_diffs: list[Decimal] = []
        rel_diffs: list[Decimal] = []
        exact = 0
        for session in common:
            left = Decimal(str(historical_by_date[session][field]))
            right = Decimal(str(official_by_date[session][field]))
            difference = abs(left - right)
            abs_diffs.append(difference)
            if difference == 0:
                exact += 1
            denominator = max(abs(left), Decimal("0.000000000001"))
            rel_diffs.append(difference / denominator)
        fields[field] = {
            "n_compared": len(common),
            "exact_match_count": exact,
            "exact_match_percent": round(100 * exact / len(common), 6) if common else 0,
            "max_absolute_difference": decimal_summary(abs_diffs, "max"),
            "median_absolute_difference": decimal_summary(abs_diffs, "median"),
            "max_relative_difference": decimal_summary(rel_diffs, "max"),
        }
    return {
        "historical_row_count": len(historical),
        "official_row_count": len(official),
        "aligned_row_count": len(common),
        "historical_only_sessions": len(historical_by_date.keys() - official_by_date.keys()),
        "official_only_sessions": len(official_by_date.keys() - historical_by_date.keys()),
        "fields": fields,
    }


def decimal_summary(values: list[Decimal], operation: str) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if operation == "max":
        result = ordered[-1]
    elif operation == "median":
        middle = len(ordered) // 2
        result = (
            ordered[middle]
            if len(ordered) % 2
            else (ordered[middle - 1] + ordered[middle]) / 2
        )
    else:
        raise ValueError(f"unsupported operation: {operation}")
    return format(result, "f")


def feature_parity_rows(
    historical_bars: dict[str, list[dict[str, object]]],
    official_bars: dict[str, list[dict[str, object]]],
    benchmark_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Compare reconstructable features without pretending close is adjusted close."""
    config = load_risk_feature_config(FEATURE_CONFIG)
    benchmark = {str(row["date"]): Decimal(str(row["price"])) for row in benchmark_rows}
    benchmark_sessions = sorted(
        session for session in benchmark if "2024-01-01" <= session <= "2025-12-31"
    )
    comparisons: dict[str, list[Decimal]] = defaultdict(list)
    relative_comparisons: dict[str, list[Decimal]] = defaultdict(list)
    missing_mismatch: dict[str, int] = defaultdict(int)
    for ticker, historical in historical_bars.items():
        historical_by_date = {str(row["trading_date"]): row for row in historical}
        official_by_date = {
            str(row["trading_date"]): row for row in official_bars.get(ticker, [])
        }
        for index in range(
            config.required_consecutive_sessions - 1, len(benchmark_sessions)
        ):
            sessions = benchmark_sessions[
                index - config.required_consecutive_sessions + 1 : index + 1
            ]
            if any(
                session not in historical_by_date or session not in official_by_date
                for session in sessions
            ):
                continue
            benchmark_window = [benchmark[session] for session in sessions]
            historical_window = [historical_by_date[session] for session in sessions]
            official_window = []
            for session in sessions:
                row = dict(official_by_date[session])
                # Placeholder is required by the frozen calculator, but adjusted-dependent
                # outputs are never evaluated or represented as reconstructed.
                row["adjusted_close"] = row["close"]
                official_window.append(row)
            historical_values = _calculate_features(historical_window, benchmark_window, config)
            official_values = _calculate_features(official_window, benchmark_window, config)
            for name in RAW_ONLY_FEATURES | BENCHMARK_ONLY_FEATURES:
                left = historical_values[name]
                right = official_values[name]
                if left is None or right is None:
                    missing_mismatch[name] += int(left != right)
                    continue
                left_decimal = Decimal(str(left))
                right_decimal = Decimal(str(right))
                difference = abs(left_decimal - right_decimal)
                comparisons[name].append(difference)
                relative_comparisons[name].append(
                    difference / max(abs(left_decimal), Decimal("0.000000000001"))
                )

    result = []
    for name in FEATURE_NAMES:
        if name not in RAW_ONLY_FEATURES | BENCHMARK_ONLY_FEATURES:
            result.append(
                {
                    "feature_name": name,
                    "status": "FAIL_NOT_EVALUABLE",
                    "n_compared": 0,
                    "missing_mismatch_count": 0,
                    "exact_match_percent": None,
                    "max_absolute_difference": None,
                    "median_absolute_difference": None,
                    "max_relative_difference": None,
                    "reason": "requires training-equivalent adjusted_close lineage",
                }
            )
            continue
        values = comparisons.get(name, [])
        relative_values = relative_comparisons.get(name, [])
        exact = sum(value == 0 for value in values)
        passed = bool(values) and all(value <= Decimal("0.000000000001") for value in values)
        result.append(
            {
                "feature_name": name,
                "status": "PASS" if passed else "FAIL",
                "n_compared": len(values),
                "missing_mismatch_count": missing_mismatch[name],
                "exact_match_percent": round(100 * exact / len(values), 6) if values else 0,
                "max_absolute_difference": decimal_summary(values, "max"),
                "median_absolute_difference": decimal_summary(values, "median"),
                "max_relative_difference": decimal_summary(relative_values, "max"),
                "reason": (
                    "same frozen benchmark input and formula"
                    if name in BENCHMARK_ONLY_FEATURES
                    else "official raw OHLCV versus frozen Yahoo raw OHLCV"
                ),
            }
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected object: {path}")
    return payload


def fetch_json(client: httpx.Client, url: str, **params: str) -> Any:
    response = client.get(url, params=params or None)
    response.raise_for_status()
    return response.json()


def collect_live_snapshot(
    start_year: int = 2024,
    end_year: int = 2025,
    *,
    current_only: bool = False,
) -> dict[str, Any]:
    market_config = load_json(MARKET_CONFIG)
    tickers = [str(row["ticker"]) for row in market_config["universe"]]
    overlap_months = [
        f"{year}{month:02d}01"
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
    ]
    current_months = ["20260701", "20260801"]
    months = current_months if current_only else overlap_months + current_months
    with httpx.Client(
        timeout=httpx.Timeout(30, connect=10),
        follow_redirects=True,
        headers={"User-Agent": "financial-ai-assistant/0.1 bounded-parity-audit"},
    ) as client:
        current_rows = fetch_json(client, TWSE_CURRENT_URL)
        tpex_rows = fetch_json(client, TPEX_CURRENT_URL)
        action_rows = fetch_json(client, TWSE_ACTION_URL)
        total_return_rows = fetch_json(client, TWSE_TOTAL_RETURN_URL)
        current_benchmark_payload = fetch_json(
            client,
            FINMIND_URL,
            dataset="TaiwanStockTotalReturnIndex",
            data_id="TAIEX",
            start_date="2026-07-01",
            end_date="2026-08-30",
        )
        historical: dict[str, list[dict[str, object]]] = {}
        month_cache_dir = CACHE_DIR / "twse_months"
        month_cache_dir.mkdir(parents=True, exist_ok=True)
        for ticker in tickers:
            for month in months:
                month_path = month_cache_dir / f"{ticker}-{month}.json"
                if month_path.exists():
                    normalized = json.loads(month_path.read_text(encoding="utf-8"))
                else:
                    payload = fetch_json(
                        client,
                        TWSE_MONTH_URL,
                        response="json",
                        date=month,
                        stockNo=ticker,
                    )
                    normalized = normalize_twse_month(payload, ticker)
                    month_path.write_text(
                        json.dumps(
                            normalized,
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    time.sleep(3.0 if current_only else 0.8)
            ticker_rows: list[dict[str, object]] = []
            for month_path in sorted(month_cache_dir.glob(f"{ticker}-*.json")):
                ticker_rows.extend(json.loads(month_path.read_text(encoding="utf-8")))
            historical[ticker] = sorted(
                ticker_rows, key=lambda row: str(row["trading_date"])
            )
    snapshot = {
        "schema_version": "f11b-official-live-audit-cache-v1",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "request_bound": {
            "twse_month_request_upper_bound": len(tickers) * len(months),
            "other_requests": 5,
            "collection_scope": "current_only" if current_only else "full_overlap",
        },
        "twse_current": parse_twse_current(current_rows),
        "tpex_current_tickers": sorted(
            {
                str(row.get("SecuritiesCompanyCode", "")).strip()
                for row in tpex_rows
                if row.get("SecuritiesCompanyCode")
            }
        ),
        "twse_action_schema": sorted(action_rows[0]) if action_rows else [],
        "twse_action_row_count": len(action_rows),
        "twse_total_return_schema": sorted(total_return_rows[0]) if total_return_rows else [],
        "twse_total_return_row_count": len(total_return_rows),
        "twse_total_return_rows": [
            {
                "date": roc_date(str(row["Date"])),
                "price": decimal_text(row["TAIEXTotalReturnIndex"]),
            }
            for row in total_return_rows
        ],
        "current_benchmark_sessions": sorted(
            {
                str(row["date"])
                for row in current_benchmark_payload.get("data", [])
                if isinstance(row, dict) and row.get("date")
            }
        ),
        "current_benchmark_rows": [
            {
                "date": str(row["date"]),
                "price": decimal_text(row["price"]),
                "stock_id": str(row["stock_id"]),
            }
            for row in current_benchmark_payload.get("data", [])
            if isinstance(row, dict)
            and row.get("date")
            and row.get("price") is not None
        ],
        "historical": historical,
    }
    snapshot["sha256"] = canonical_hash(snapshot)
    return snapshot


def build_derived_audit(snapshot: dict[str, Any]) -> dict[str, Any]:
    market_config = load_json(MARKET_CONFIG)
    feature_config = load_json(FEATURE_CONFIG)
    historical_dataset = load_json(HISTORICAL_DATASET)
    tickers = [str(row["ticker"]) for row in market_config["universe"]]
    historical_by_ticker: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in historical_dataset["stock_rows"]:
        if "2024-01-01" <= str(row["trading_date"]) <= "2025-12-31":
            historical_by_ticker[str(row["ticker"])].append(row)
    official_by_ticker = snapshot["historical"]
    coverage = []
    exchange_sessions = snapshot["current_benchmark_sessions"]
    latest_exchange_session = exchange_sessions[-1]
    required_sessions = exchange_sessions[-35:]
    for ticker in tickers:
        current = snapshot["twse_current"].get(ticker)
        official_sessions = {
            str(row["trading_date"])
            for row in official_by_ticker[ticker]
            if str(row["trading_date"]) in required_sessions
        }
        coverage.append(
            {
                "ticker": ticker,
                "market": "TWSE" if current else "UNRESOLVED",
                "official_source": "TWSE_STOCK_DAY_ALL" if current else None,
                "latest_available_session": current.get("trading_date") if current else None,
                "latest_exchange_session": latest_exchange_session,
                "required_recent_sessions": len(required_sessions),
                "covered_recent_sessions": len(official_sessions),
                "missing_recent_sessions": sorted(set(required_sessions) - official_sessions),
                "stale": not current
                or current["trading_date"] != latest_exchange_session,
                "missing": current is None,
                "provider_warning": None,
                "usable": current is not None
                and current["trading_date"] == latest_exchange_session
                and len(official_sessions) == len(required_sessions),
                "tpex_duplicate_mapping": ticker in snapshot["tpex_current_tickers"],
            }
        )
    ohlcv = {
        ticker: compare_numeric_rows(
            historical_by_ticker[ticker], official_by_ticker[ticker]
        )
        for ticker in tickers
    }
    feature_rows = feature_parity_rows(
        historical_by_ticker,
        official_by_ticker,
        historical_dataset["benchmark_rows"],
    )
    official_benchmark = {
        str(row["date"]): Decimal(str(row["price"]))
        for row in snapshot["twse_total_return_rows"]
    }
    candidate_benchmark = {
        str(row["date"]): Decimal(str(row["price"]))
        for row in snapshot["current_benchmark_rows"]
        if row["stock_id"] == "TAIEX"
    }
    benchmark_common = sorted(official_benchmark.keys() & candidate_benchmark.keys())
    benchmark_diffs = [
        abs(official_benchmark[session] - candidate_benchmark[session])
        for session in benchmark_common
    ]
    derived = {
        "schema_version": "f11b-official-current-market-derived-audit-v1",
        "source_snapshot_sha256": snapshot["sha256"],
        "frozen_contract": {
            "universe": tickers,
            "feature_names": feature_config["feature_names"],
            "feature_count": len(feature_config["feature_names"]),
            "feature_pipeline_version": feature_config["pipeline_version"],
            "feature_contract_sha256": canonical_hash(feature_config),
            "historical_stock_source": market_config["stock_source"],
            "historical_adjusted_close_field": "Yahoo chart indicators.adjclose",
            "benchmark_dataset": market_config["benchmark_dataset_id"],
            "benchmark_id": market_config["benchmark_id"],
        },
        "coverage": coverage,
        "ohlcv_parity": ohlcv,
        "feature_parity": feature_rows,
        "benchmark_parity": {
            "historical_identity": "TAIEX total-return index",
            "official_dataset": "TWSE MFI94U TAIEXTotalReturnIndex",
            "current_candidate_dataset": "FinMind TaiwanStockTotalReturnIndex/TAIEX",
            "n_compared": len(benchmark_common),
            "exact_match_count": sum(value == 0 for value in benchmark_diffs),
            "max_absolute_difference": decimal_summary(benchmark_diffs, "max"),
            "median_absolute_difference": decimal_summary(benchmark_diffs, "median"),
            "pass": bool(benchmark_diffs) and all(value == 0 for value in benchmark_diffs),
        },
        "corporate_action_evidence": {
            "openapi_endpoint": TWSE_ACTION_URL,
            "returned_schema": snapshot["twse_action_schema"],
            "returned_row_count": snapshot["twse_action_row_count"],
            "historical_endpoint_in_twse_openapi_schema": False,
            "training_equivalence_proven": False,
        },
    }
    derived["sha256"] = canonical_hash(derived)
    return derived


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect-live", action="store_true")
    parser.add_argument("--current-only", action="store_true")
    parser.add_argument("--derive", action="store_true")
    args = parser.parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = CACHE_DIR / "normalized_official_snapshot.json"
    if args.collect_live:
        snapshot = collect_live_snapshot(current_only=args.current_only)
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"stored ignored normalized snapshot sha256={snapshot['sha256']}")
    if args.derive:
        snapshot = load_json(snapshot_path)
        derived = build_derived_audit(snapshot)
        output = CACHE_DIR / "derived_audit.json"
        output.write_text(
            json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        passed = sum(row["status"] == "PASS" for row in derived["feature_parity"])
        print(f"stored ignored derived audit sha256={derived['sha256']} feature_pass={passed}/23")


if __name__ == "__main__":
    main()
