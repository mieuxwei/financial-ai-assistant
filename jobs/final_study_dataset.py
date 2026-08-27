from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.features.final_study_builder import (
    build_final_study_dataset,
    write_immutable_json,
    write_report,
)
from pipelines.features.risk_builder import load_risk_feature_config
from research.planning.final_study_protocol import load_final_study_config

DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_FEATURE_CONFIG = Path("research/configs/risk_features.v1.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_OUTPUT = Path(".tools/datasets/final-volatility-surprise-dataset-v1/dataset.json")
DEFAULT_REPORT = Path("artifacts/f2-final-study-dataset-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the leakage-safe F2 final-study dataset")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--feature-config", type=Path, default=DEFAULT_FEATURE_CONFIG)
    parser.add_argument("--market-dataset", type=Path, default=DEFAULT_MARKET_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def build(
    protocol_path: Path,
    feature_config_path: Path,
    market_dataset_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (market_dataset_path, output_path, report_path):
        _require_local_data_path(path)
    protocol = load_final_study_config(protocol_path)
    feature_config = load_risk_feature_config(feature_config_path)
    market_dataset = json.loads(market_dataset_path.read_text(encoding="utf-8"))
    dataset, report = build_final_study_dataset(protocol, feature_config, market_dataset)
    write_immutable_json(output_path, dataset)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "dataset": str(output_path),
        "report": str(report_path),
        "dataset_sha256": report["dataset_sha256"],
        "eligible_row_count": report["eligible_row_count"],
        "excluded_row_count": report["excluded_row_count"],
        "preprocessing_fitted": False,
        "models_trained": False,
        "binary_labels_materialized": False,
    }


def _require_local_data_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F2 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = build(
        args.protocol,
        args.feature_config,
        args.market_dataset,
        args.output,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
