from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.operating_points import write_immutable_json, write_report
from research.evaluation.regime_thresholds import analyze_regime_thresholds, load_config
from research.modeling.baselines import load_risk_baseline_config, verify_feature_dataset
from research.modeling.temporal_validation import load_risk_temporal_validation_config

DEFAULT_CONFIG = Path("research/configs/post_m8_regime_thresholds.v1.json")
DEFAULT_TEMPORAL_CONFIG = Path("research/configs/risk_temporal_validation.v1.json")
DEFAULT_BASELINE_CONFIG = Path("research/configs/risk_baselines.v1.json")
DEFAULT_FEATURE_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_OOF_DATASET = Path(".tools/evaluations/post-m8-development-oof-v1/dataset.json")
DEFAULT_M10_REPORT = Path("artifacts/m10-operating-point-report.json")
DEFAULT_ANALYSIS = Path(".tools/evaluations/post-m8-regime-thresholds-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/m11-regime-threshold-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run development-only M11 regime thresholds")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--temporal-config", type=Path, default=DEFAULT_TEMPORAL_CONFIG)
    parser.add_argument("--baseline-config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    parser.add_argument("--feature-dataset", type=Path, default=DEFAULT_FEATURE_DATASET)
    parser.add_argument("--oof-dataset", type=Path, default=DEFAULT_OOF_DATASET)
    parser.add_argument("--m10-report", type=Path, default=DEFAULT_M10_REPORT)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    for path in (
        args.feature_dataset,
        args.oof_dataset,
        args.m10_report,
        args.analysis,
        args.report,
    ):
        _require_scoped_path(path)
    config = load_config(args.config)
    temporal = load_risk_temporal_validation_config(args.temporal_config)
    baseline = load_risk_baseline_config(args.baseline_config)
    feature_dataset = json.loads(args.feature_dataset.read_text(encoding="utf-8"))
    verify_feature_dataset(baseline, feature_dataset)
    development_dataset = json.loads(args.oof_dataset.read_text(encoding="utf-8"))
    m10_report = json.loads(args.m10_report.read_text(encoding="utf-8"))
    analysis, report = analyze_regime_thresholds(
        config, temporal, feature_dataset, development_dataset, m10_report
    )
    write_immutable_json(args.analysis, analysis)
    write_report(args.report, report)
    return {
        "passed": True,
        "analysis": str(args.analysis),
        "report": str(args.report),
        "analysis_sha256": analysis["sha256"],
        "selection_status": report["selection_status"],
        "sealed_test_rows_used": 0,
        "m7_rerun_performed": False,
    }


def _require_scoped_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M11 inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    print(json.dumps(run(build_parser().parse_args()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
