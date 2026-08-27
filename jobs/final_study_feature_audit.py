from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.features.final_study_builder import write_report
from pipelines.features.risk_builder import load_risk_feature_config
from research.evaluation.final_study_feature_audit import (
    audit_final_study_dataset,
    load_coverage_audit_config,
)
from research.planning.final_study_protocol import load_final_study_config

DEFAULT_AUDIT_CONFIG = Path("research/configs/final_study_coverage_bias_audit.v1.json")
DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_FEATURE_CONFIG = Path("research/configs/risk_features.v1.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_FINAL_DATASET = Path(
    ".tools/datasets/final-volatility-surprise-dataset-v1/dataset.json"
)
DEFAULT_REPORT = Path("artifacts/f3-final-study-target-feature-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit the frozen F3 target/feature contract")
    parser.add_argument("--audit-config", type=Path, default=DEFAULT_AUDIT_CONFIG)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--feature-config", type=Path, default=DEFAULT_FEATURE_CONFIG)
    parser.add_argument("--market-dataset", type=Path, default=DEFAULT_MARKET_DATASET)
    parser.add_argument("--final-dataset", type=Path, default=DEFAULT_FINAL_DATASET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def audit(
    audit_config_path: Path,
    protocol_path: Path,
    feature_config_path: Path,
    market_dataset_path: Path,
    final_dataset_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (market_dataset_path, final_dataset_path, report_path):
        _require_local_data_path(path)
    config = load_coverage_audit_config(audit_config_path)
    protocol = load_final_study_config(protocol_path)
    feature_config = load_risk_feature_config(feature_config_path)
    market_dataset = json.loads(market_dataset_path.read_text(encoding="utf-8"))
    dataset = json.loads(final_dataset_path.read_text(encoding="utf-8"))
    report = audit_final_study_dataset(
        config,
        protocol,
        feature_config,
        market_dataset,
        dataset,
    )
    write_report(report_path, report)
    coverage = report["coverage_bias_audit"]
    return {
        "passed": report["passed"],
        "report": str(report_path),
        "dataset_sha256": report["dataset_sha256"],
        "coverage_warning_downgrade_allowed": coverage[
            "coverage_warning_downgrade_allowed"
        ],
        "coverage_conclusion": coverage["conclusion"],
        "abnormal_concentration_count": len(
            coverage["abnormal_concentration_findings"]
        ),
        "models_trained": False,
        "preprocessing_fitted": False,
    }


def _require_local_data_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F3 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = audit(
        args.audit_config,
        args.protocol,
        args.feature_config,
        args.market_dataset,
        args.final_dataset,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
