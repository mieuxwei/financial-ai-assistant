from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.features.risk_builder import (
    build_risk_feature_dataset,
    load_risk_feature_config,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/risk_features.v1.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_LABEL_DATASET = Path(
    ".tools/datasets/next-session-volatility-risk-v1/dataset.json"
)
DEFAULT_OUTPUT = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_REPORT = Path("artifacts/m3-risk-feature-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build leakage-safe M3 market-risk features")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--market-dataset", type=Path, default=DEFAULT_MARKET_DATASET)
    parser.add_argument("--label-dataset", type=Path, default=DEFAULT_LABEL_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def build(
    config_path: Path,
    market_dataset_path: Path,
    label_dataset_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (market_dataset_path, label_dataset_path, output_path, report_path):
        _require_ignored_path(path)
    config = load_risk_feature_config(config_path)
    market_dataset = json.loads(market_dataset_path.read_text(encoding="utf-8"))
    label_dataset = json.loads(label_dataset_path.read_text(encoding="utf-8"))
    dataset, report = build_risk_feature_dataset(config, market_dataset, label_dataset)
    write_immutable_json(output_path, dataset)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "dataset": str(output_path),
        "report": str(report_path),
        "feature_count": report["feature_count"],
        "materialized_row_counts": report["materialized_row_counts"],
        "sealed_test_features_materialized": False,
        "preprocessing_fitted": False,
        "models_trained": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M3 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = build(
        args.config,
        args.market_dataset,
        args.label_dataset,
        args.output,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
