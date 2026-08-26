from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.core.database import SessionLocal
from backend.app.repositories.market_data import MarketDataRepository
from backend.app.services.market_data import MarketDataIngestionService
from pipelines.market_data.finmind_benchmark import (
    fetch_taiex_total_return,
    write_benchmark_snapshot,
)
from pipelines.market_data.risk_dataset import (
    build_risk_market_dataset,
    load_risk_market_config,
    write_immutable_json,
    write_report,
)
from pipelines.market_data.types import MarketBar, MarketDataRequest
from pipelines.market_data.yahoo import YahooFinanceProvider

DEFAULT_CONFIG = Path("research/configs/risk_market_dataset.v1.json")
DEFAULT_BENCHMARK = Path(".tools/datasets/risk-market-dataset-v1/benchmark.json")
DEFAULT_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_REPORT = Path("artifacts/m1-risk-market-dataset-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the M1 risk-market dataset")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("ingest-stocks", "fetch-benchmark", "build"):
        item = subparsers.add_parser(command)
        item.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    benchmark = subparsers.choices["fetch-benchmark"]
    benchmark.add_argument("--output", type=Path, default=DEFAULT_BENCHMARK)
    build = subparsers.choices["build"]
    build.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    build.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    build.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def ingest_stocks(config_path: Path) -> dict[str, object]:
    config = load_risk_market_config(config_path)
    succeeded = []
    failures = []
    total_rows = 0
    with YahooFinanceProvider() as provider:
        for instrument in config.universe:
            request = MarketDataRequest(
                ticker=instrument.ticker,
                provider_symbol=instrument.provider_symbol,
                start_date=config.snapshot_start,
                end_date=config.test_end,
            )
            try:
                with SessionLocal() as session:
                    result = MarketDataIngestionService(session, provider).ingest([request])
                succeeded.append(instrument.ticker)
                total_rows += result.records_upserted
            except Exception as error:
                failures.append(
                    {"ticker": instrument.ticker, "error_code": type(error).__name__}
                )
    return {
        "succeeded": succeeded,
        "failures": failures,
        "records_upserted": total_rows,
        "contains_secrets": False,
    }


def fetch_benchmark(config_path: Path, output: Path) -> dict[str, object]:
    _require_ignored_output(output)
    config = load_risk_market_config(config_path)
    snapshot = fetch_taiex_total_return(config.snapshot_start, config.test_end)
    write_benchmark_snapshot(output, snapshot)
    return {
        "output": str(output),
        "row_count": len(snapshot["rows"]),
        "sha256": snapshot["sha256"],
        "contains_secrets": False,
    }


def build_dataset(
    config_path: Path, benchmark_path: Path, dataset_path: Path, report_path: Path
) -> dict[str, object]:
    _require_ignored_output(benchmark_path)
    _require_ignored_output(dataset_path)
    config = load_risk_market_config(config_path)
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        rows = MarketDataRepository(session).list_bars(
            tickers=[item.ticker for item in config.universe],
            start_date=config.snapshot_start,
            end_date=config.test_end,
            source=config.stock_source,
        )
    bars = [
        MarketBar(
            ticker=row.ticker,
            trading_date=row.trading_date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            adjusted_close=row.adjusted_close,
            volume=row.volume,
            source=row.source,
        )
        for row in rows
    ]
    dataset, report = build_risk_market_dataset(config, bars, benchmark)
    write_immutable_json(dataset_path, dataset)
    write_report(report_path, report)
    return {
        "dataset": str(dataset_path),
        "report": str(report_path),
        "passed": report["passed"],
        "stock_row_count": report["stock_row_count"],
        "benchmark_session_count": report["benchmark_session_count"],
        "dataset_sha256": report["dataset_sha256"],
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
    }


def _require_ignored_output(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("generated M1 data must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "ingest-stocks":
        result = ingest_stocks(args.config)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not result["failures"] else 2
    if args.command == "fetch-benchmark":
        print(json.dumps(fetch_benchmark(args.config, args.output), ensure_ascii=False))
        return 0
    result = build_dataset(args.config, args.benchmark, args.dataset, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
