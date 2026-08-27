from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.risk_labels.protocol import (
    build_risk_label_dataset,
    load_risk_label_config,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/next_session_volatility_risk.v1.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_OUTPUT_DIR = Path(".tools/datasets/next-session-volatility-risk-v1")
DEFAULT_REPORT = Path("artifacts/m2-risk-label-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build leakage-safe M2 risk labels")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--market-dataset", type=Path, default=DEFAULT_MARKET_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def build(
    config_path: Path,
    market_dataset_path: Path,
    output_dir: Path,
    report_path: Path,
) -> dict[str, object]:
    _require_ignored_path(market_dataset_path)
    _require_ignored_path(output_dir)
    _require_ignored_path(report_path)
    config = load_risk_label_config(config_path)
    market_dataset = json.loads(market_dataset_path.read_text(encoding="utf-8"))
    dataset, threshold, report = build_risk_label_dataset(config, market_dataset)
    write_immutable_json(output_dir / "dataset.json", dataset)
    write_immutable_json(output_dir / "threshold.json", threshold)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "dataset": str(output_dir / "dataset.json"),
        "threshold": str(output_dir / "threshold.json"),
        "report": str(report_path),
        "materialized_row_counts": report["materialized_row_counts"],
        "sealed_test_rows_materialized": False,
        "sealed_test_outcomes_inspected": False,
        "models_trained": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M2 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = build(args.config, args.market_dataset, args.output_dir, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
