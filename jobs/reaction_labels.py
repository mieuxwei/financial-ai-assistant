from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.models import ArticleTicker, MarketPrice, NewsArticle
from research.evaluation.market_reaction import (
    ReactionConfig,
    ReactionEvent,
    ReactionPrice,
    build_market_reaction_labels,
    reaction_snapshot_sha256,
)

DEFAULT_CONFIG = Path("research/configs/market_reaction_labeling.v1.json")
DEFAULT_MARKET_CONFIG = Path(".tools/configs/m8_market_universe.json")
DEFAULT_BENCHMARK = Path(".tools/datasets/benchmarks/finmind-taiex-total-return.json")
DEFAULT_OUTPUT_DIR = Path(".tools/reaction-labels/market-reaction-v1")
DEFAULT_REPORT = Path("artifacts/m8-market-reaction-build-report.json")


def load_config(path: Path) -> ReactionConfig:
    return ReactionConfig.model_validate_json(path.read_text(encoding="utf-8"))


def prepare_market_config(output: Path) -> dict[str, object]:
    _require_tools_path(output)
    with SessionLocal() as session:
        rows = session.execute(
            select(NewsArticle.published_at, ArticleTicker.ticker)
            .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
            .where(
                NewsArticle.source == "twse_material",
                NewsArticle.source_type == "official_announcement",
            )
            .order_by(NewsArticle.published_at, ArticleTicker.ticker)
        ).all()
    if not rows:
        raise ValueError("no official TWSE events are available")
    tickers = sorted({ticker for _, ticker in rows})
    timestamps = [_as_utc(value) for value, _ in rows]
    start_date = min(value.date() for value in timestamps) - timedelta(days=7)
    end_date = max(value.date() for value in timestamps) + timedelta(days=7)
    payload = {
        "instruments": [
            {"ticker": ticker, "provider_symbol": f"{ticker}.TW"} for ticker in tickers
        ],
        "m8_window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "event_count": len(rows),
            "distinct_ticker_count": len(tickers),
        },
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    _write_immutable(
        output,
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    )
    return payload


def build_reaction_artifacts(
    config: ReactionConfig,
    benchmark_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    _require_tools_path(output_dir)
    benchmark_snapshot = json.loads(benchmark_path.read_text(encoding="utf-8"))
    _verify_benchmark_snapshot(benchmark_snapshot)
    benchmark_prices = {
        date.fromisoformat(row["date"]): Decimal(str(row["price"]))
        for row in benchmark_snapshot["rows"]
    }
    with SessionLocal() as session:
        event_rows = session.execute(
            select(NewsArticle, ArticleTicker)
            .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
            .where(
                NewsArticle.source == "twse_material",
                NewsArticle.source_type == "official_announcement",
            )
            .order_by(NewsArticle.published_at, NewsArticle.id, ArticleTicker.ticker)
        ).all()
        tickers = sorted({link.ticker for _, link in event_rows})
        price_rows = list(
            session.scalars(
                select(MarketPrice)
                .where(
                    MarketPrice.ticker.in_(tickers),
                    MarketPrice.source == config.stock_source,
                )
                .order_by(MarketPrice.ticker, MarketPrice.trading_date)
            )
        )

    deduplicated_events: dict[tuple[str, str], ReactionEvent] = {}
    for article, link in event_rows:
        event_group_id = _event_group_id(link.ticker, article.title_fingerprint)
        identity = (event_group_id, link.ticker)
        deduplicated_events.setdefault(
            identity,
            ReactionEvent(
                article_id=article.id,
                event_group_id=event_group_id,
                ticker=link.ticker,
                published_at=_as_utc(article.published_at),
            ),
        )
    events = list(deduplicated_events.values())
    prices = [
        ReactionPrice(
            ticker=row.ticker,
            trading_date=row.trading_date,
            adjusted_close=row.adjusted_close,
        )
        for row in price_rows
    ]
    market_snapshot_sha256 = _market_snapshot_sha256(
        prices, str(benchmark_snapshot["sha256"]), config
    )
    labels = build_market_reaction_labels(
        events,
        prices,
        benchmark_prices,
        config,
        market_snapshot_sha256=market_snapshot_sha256,
    )
    split_rows = {"train": [], "validation": [], "test": [], "unassigned": []}
    for row in labels:
        split_rows[str(row["split_assignment"])].append(row)
    split_files = {}
    for split, rows in split_rows.items():
        rows.sort(key=lambda row: (row["published_at"], row["event_group_id"], row["horizon"]))
        payload = _jsonl_bytes(rows)
        target = output_dir / f"{split}.jsonl"
        _write_immutable(target, payload)
        split_files[split] = {
            "row_count": len(rows),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "abstained_count": sum(bool(row["abstained"]) for row in rows),
            "reaction_class_counts": (
                None
                if split == "test"
                else dict(
                    sorted(
                        Counter(
                            str(row["reaction_class"])
                            for row in rows
                            if not row["abstained"]
                        ).items()
                    )
                )
            ),
        }
    historical_train_validation_ready = bool(
        split_rows["train"] and split_rows["validation"]
    )
    return {
        "report_version": "m8-market-reaction-build-report-v1",
        "protocol_version": config.protocol_version,
        "event_input_count": len(event_rows),
        "deduplicated_event_count": len(events),
        "duplicate_event_count": len(event_rows) - len(events),
        "stock_price_count": len(prices),
        "benchmark_session_count": len(benchmark_prices),
        "benchmark_snapshot_sha256": benchmark_snapshot["sha256"],
        "market_snapshot_sha256": market_snapshot_sha256,
        "reaction_snapshot_sha256": reaction_snapshot_sha256(labels),
        "split_files": split_files,
        "status": (
            "ready"
            if historical_train_validation_ready
            else "implementation_complete_historical_backfill_required"
        ),
        "historical_train_validation_ready": historical_train_validation_ready,
        "test_target_metrics_withheld": True,
        "future_values_are_target_side_only": True,
        "raw_event_text_stored": False,
        "manual_labels_used": False,
        "manual_review_used": False,
        "sentiment_ground_truth": False,
    }


def _verify_benchmark_snapshot(snapshot: dict[str, object]) -> None:
    expected = snapshot.get("sha256")
    content = {key: value for key, value in snapshot.items() if key != "sha256"}
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    if observed != expected:
        raise ValueError("benchmark snapshot SHA-256 mismatch")
    if snapshot.get("dataset_id") != "TaiwanStockTotalReturnIndex":
        raise ValueError("unexpected benchmark dataset")
    if snapshot.get("benchmark_id") != "TAIEX":
        raise ValueError("unexpected benchmark identifier")


def _market_snapshot_sha256(
    prices: list[ReactionPrice], benchmark_sha256: str, config: ReactionConfig
) -> str:
    rows = [
        {
            "ticker": row.ticker,
            "trading_date": row.trading_date.isoformat(),
            "adjusted_close": format(row.adjusted_close, "f"),
        }
        for row in sorted(prices, key=lambda item: (item.ticker, item.trading_date))
    ]
    payload = {
        "stock_source": config.stock_source,
        "benchmark_source": config.benchmark_source,
        "benchmark_sha256": benchmark_sha256,
        "rows": rows,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _event_group_id(ticker: str, title_fingerprint: str) -> str:
    return hashlib.sha256(f"{ticker}\x1f{title_fingerprint}".encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _jsonl_bytes(rows: list[dict[str, object]]) -> bytes:
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite a different existing file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _require_tools_path(path: Path) -> None:
    if not path.resolve().is_relative_to((Path.cwd() / ".tools").resolve()):
        raise ValueError("M8 generated inputs and targets must stay inside .tools/")


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and build M8 market-reaction targets")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare-market-config")
    prepare.add_argument("--output", type=Path, default=DEFAULT_MARKET_CONFIG)
    build = subparsers.add_parser("build")
    build.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    build.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    build.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    build.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare-market-config":
        payload = prepare_market_config(args.output)
        print(
            json.dumps(
                {"output": str(args.output), **payload["m8_window"]},
                ensure_ascii=False,
            )
        )
        return 0
    report = build_reaction_artifacts(
        load_config(args.config), args.benchmark, args.output_dir
    )
    write_report(args.report, report)
    print(
        json.dumps(
            {
                "report": str(args.report),
                "deduplicated_event_count": report["deduplicated_event_count"],
                "stock_price_count": report["stock_price_count"],
                "benchmark_session_count": report["benchmark_session_count"],
                "test_target_metrics_withheld": True,
                "manual_labels_used": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
