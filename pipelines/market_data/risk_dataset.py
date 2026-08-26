from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipelines.market_data.types import MarketBar

CONFIG_VERSION = "risk-market-dataset-config-v1"
DATASET_VERSION = "risk-market-dataset-v1"


class RiskInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticker: str = Field(pattern=r"^[0-9A-Z]{2,12}$")
    provider_symbol: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)


class RiskMarketDatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-market-dataset-config-v1"] = CONFIG_VERSION
    dataset_version: Literal["risk-market-dataset-v1"] = DATASET_VERSION
    market_timezone: str = Field(min_length=1, max_length=100)
    stock_source: str = Field(min_length=1, max_length=100)
    stock_source_terms_url: str = Field(min_length=1, max_length=500)
    benchmark_dataset_id: str = Field(min_length=1, max_length=100)
    benchmark_id: str = Field(min_length=1, max_length=100)
    benchmark_source: str = Field(min_length=1, max_length=100)
    benchmark_source_terms_url: str = Field(min_length=1, max_length=500)
    snapshot_start: date
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    minimum_warmup_sessions: int = Field(ge=1)
    minimum_train_sessions: int = Field(ge=1)
    minimum_validation_sessions: int = Field(ge=1)
    minimum_test_sessions: int = Field(ge=1)
    maximum_missing_session_ratio: float = Field(ge=0, le=0.2)
    universe: tuple[RiskInstrument, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_contract(self) -> RiskMarketDatasetConfig:
        if not (
            self.snapshot_start
            < self.train_start
            <= self.train_end
            < self.validation_start
            <= self.validation_end
            < self.test_start
            <= self.test_end
        ):
            raise ValueError("warmup/train/validation/test periods must be ordered and disjoint")
        tickers = [item.ticker for item in self.universe]
        symbols = [item.provider_symbol for item in self.universe]
        if len(tickers) != len(set(tickers)):
            raise ValueError("universe tickers must be unique")
        if len(symbols) != len(set(symbols)):
            raise ValueError("provider symbols must be unique")
        return self

    def split_for(self, value: date) -> str | None:
        if self.snapshot_start <= value < self.train_start:
            return "warmup"
        if self.train_start <= value <= self.train_end:
            return "train"
        if self.validation_start <= value <= self.validation_end:
            return "validation"
        if self.test_start <= value <= self.test_end:
            return "test"
        return None


def load_risk_market_config(path: Path) -> RiskMarketDatasetConfig:
    return RiskMarketDatasetConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_risk_market_dataset(
    config: RiskMarketDatasetConfig,
    stock_bars: list[MarketBar],
    benchmark_snapshot: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    _verify_benchmark_snapshot(benchmark_snapshot, config)
    benchmark_rows = _normalize_benchmark_rows(benchmark_snapshot, config)
    benchmark_sessions = [date.fromisoformat(str(row["date"])) for row in benchmark_rows]
    benchmark_by_split = Counter(
        split for value in benchmark_sessions if (split := config.split_for(value)) is not None
    )
    benchmark_session_set = set(benchmark_sessions)

    allowed_tickers = {item.ticker for item in config.universe}
    normalized_stock_rows: list[dict[str, object]] = []
    rows_by_ticker: dict[str, list[MarketBar]] = defaultdict(list)
    fatal_issues: list[str] = []
    seen: set[tuple[str, date]] = set()
    for bar in sorted(stock_bars, key=lambda item: (item.ticker, item.trading_date)):
        if bar.ticker not in allowed_tickers:
            continue
        if bar.source != config.stock_source:
            fatal_issues.append(f"unexpected source for {bar.ticker}: {bar.source}")
            continue
        if not config.snapshot_start <= bar.trading_date <= config.test_end:
            continue
        identity = (bar.ticker, bar.trading_date)
        if identity in seen:
            fatal_issues.append(f"duplicate stock session: {bar.ticker} {bar.trading_date}")
            continue
        seen.add(identity)
        _validate_bar(bar, fatal_issues)
        rows_by_ticker[bar.ticker].append(bar)
        normalized_stock_rows.append(_bar_payload(bar, config))

    ticker_reports = []
    for instrument in config.universe:
        ticker_rows = rows_by_ticker.get(instrument.ticker, [])
        observed_sessions = {row.trading_date for row in ticker_rows}
        split_counts = Counter(
            split
            for row in ticker_rows
            if (split := config.split_for(row.trading_date)) is not None
        )
        missing_by_split: dict[str, int] = {}
        missing_hashes: dict[str, str] = {}
        missing_ratio_by_split: dict[str, float] = {}
        for split in ("warmup", "train", "validation", "test"):
            expected = [
                value
                for value in benchmark_sessions
                if config.split_for(value) == split
            ]
            missing = [value for value in expected if value not in observed_sessions]
            missing_by_split[split] = len(missing)
            missing_ratio = len(missing) / len(expected) if expected else 1.0
            missing_ratio_by_split[split] = round(missing_ratio, 10)
            missing_hashes[split] = _hash([value.isoformat() for value in missing])
            if missing_ratio > config.maximum_missing_session_ratio:
                fatal_issues.append(
                    f"{instrument.ticker} {split} missing-session ratio {missing_ratio:.6f} "
                    f"exceeds {config.maximum_missing_session_ratio:.6f}"
                )
        minimums = {
            "warmup": config.minimum_warmup_sessions,
            "train": config.minimum_train_sessions,
            "validation": config.minimum_validation_sessions,
            "test": config.minimum_test_sessions,
        }
        for split, minimum in minimums.items():
            if split_counts[split] < minimum:
                fatal_issues.append(
                    f"{instrument.ticker} {split} has {split_counts[split]} sessions; "
                    f"minimum is {minimum}"
                )
        extra_sessions = sorted(observed_sessions - benchmark_session_set)
        ticker_reports.append(
            {
                "ticker": instrument.ticker,
                "name": instrument.name,
                "row_count": len(ticker_rows),
                "first_date": ticker_rows[0].trading_date.isoformat() if ticker_rows else None,
                "last_date": ticker_rows[-1].trading_date.isoformat() if ticker_rows else None,
                "split_session_counts": dict(sorted(split_counts.items())),
                "missing_session_counts": missing_by_split,
                "missing_session_ratios": missing_ratio_by_split,
                "missing_session_hashes": missing_hashes,
                "extra_benchmark_session_count": len(extra_sessions),
                "extra_benchmark_session_hash": _hash(
                    [value.isoformat() for value in extra_sessions]
                ),
                "zero_volume_count": sum(row.volume == 0 for row in ticker_rows),
            }
        )

    dataset_content = {
        "schema_version": DATASET_VERSION,
        "config": config.model_dump(mode="json"),
        "benchmark_snapshot_sha256": benchmark_snapshot["sha256"],
        "benchmark_rows": benchmark_rows,
        "stock_rows": normalized_stock_rows,
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
    }
    dataset_sha256 = _hash(dataset_content)
    dataset = {**dataset_content, "sha256": dataset_sha256}
    unique_fatal_issues = list(dict.fromkeys(fatal_issues))
    report = {
        "report_version": "m1-risk-market-dataset-audit-v1",
        "dataset_version": config.dataset_version,
        "dataset_sha256": dataset_sha256,
        "benchmark_snapshot_sha256": benchmark_snapshot["sha256"],
        "stock_row_count": len(normalized_stock_rows),
        "benchmark_session_count": len(benchmark_rows),
        "benchmark_split_session_counts": dict(sorted(benchmark_by_split.items())),
        "ticker_count": len(config.universe),
        "ticker_reports": ticker_reports,
        "fatal_issues": unique_fatal_issues,
        "passed": not unique_fatal_issues,
        "raw_rows_in_report": False,
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
        "manual_labels_used": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return dataset, report


def write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise FileExistsError(f"refusing to overwrite a different immutable file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_benchmark_snapshot(
    snapshot: dict[str, object], config: RiskMarketDatasetConfig
) -> None:
    expected = snapshot.get("sha256")
    content = {key: value for key, value in snapshot.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError("benchmark snapshot SHA-256 mismatch")
    if snapshot.get("dataset_id") != config.benchmark_dataset_id:
        raise ValueError("unexpected benchmark dataset")
    if snapshot.get("benchmark_id") != config.benchmark_id:
        raise ValueError("unexpected benchmark identifier")


def _normalize_benchmark_rows(
    snapshot: dict[str, object], config: RiskMarketDatasetConfig
) -> list[dict[str, object]]:
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise TypeError("benchmark snapshot rows must be a list")
    normalized = []
    seen_dates = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise TypeError("benchmark row must be an object")
        value = date.fromisoformat(str(raw["date"]))
        if not config.snapshot_start <= value <= config.test_end:
            continue
        if value in seen_dates:
            raise ValueError(f"duplicate benchmark session: {value}")
        seen_dates.add(value)
        price = float(raw["price"])
        if price <= 0:
            raise ValueError(f"non-positive benchmark price: {value}")
        normalized.append(
            {
                "date": value.isoformat(),
                "price": str(raw["price"]),
                "stock_id": str(raw["stock_id"]),
            }
        )
    normalized.sort(key=lambda row: str(row["date"]))
    if not normalized:
        raise ValueError("benchmark snapshot has no rows in the configured period")
    return normalized


def _validate_bar(bar: MarketBar, fatal_issues: list[str]) -> None:
    prices = (bar.open, bar.high, bar.low, bar.close, bar.adjusted_close)
    if min(prices) <= 0:
        fatal_issues.append(f"non-positive stock price: {bar.ticker} {bar.trading_date}")
    if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
        fatal_issues.append(f"invalid OHLC range: {bar.ticker} {bar.trading_date}")
    if bar.high < bar.low:
        fatal_issues.append(f"high below low: {bar.ticker} {bar.trading_date}")
    if bar.volume < 0:
        fatal_issues.append(f"negative volume: {bar.ticker} {bar.trading_date}")


def _bar_payload(bar: MarketBar, config: RiskMarketDatasetConfig) -> dict[str, object]:
    return {
        "ticker": bar.ticker,
        "trading_date": bar.trading_date.isoformat(),
        "split": config.split_for(bar.trading_date),
        "open": format(bar.open, "f"),
        "high": format(bar.high, "f"),
        "low": format(bar.low, "f"),
        "close": format(bar.close, "f"),
        "adjusted_close": format(bar.adjusted_close, "f"),
        "volume": bar.volume,
        "source": bar.source,
    }


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
