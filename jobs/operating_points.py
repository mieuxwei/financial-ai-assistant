from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.operating_points import (
    analyze_operating_points,
    load_config,
    reconstruct_development_oof,
    write_immutable_json,
    write_report,
)
from research.modeling.baselines import load_risk_baseline_config
from research.modeling.temporal_validation import load_risk_temporal_validation_config
from research.modeling.tree_models import load_risk_tree_model_config

DEFAULT_CONFIG = Path("research/configs/post_m8_operating_points.v1.json")
DEFAULT_TEMPORAL_CONFIG = Path("research/configs/risk_temporal_validation.v1.json")
DEFAULT_BASELINE_CONFIG = Path("research/configs/risk_baselines.v1.json")
DEFAULT_TREE_CONFIG = Path("research/configs/risk_tree_models.v1.json")
DEFAULT_FEATURE_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_CANDIDATE_MANIFEST = Path(".tools/models/risk-final-candidate-v1/manifest.json")
DEFAULT_M6_REPORT = Path("artifacts/m6-risk-temporal-validation-report.json")
DEFAULT_OOF_DATASET = Path(".tools/evaluations/post-m8-development-oof-v1/dataset.json")
DEFAULT_ANALYSIS = Path(".tools/evaluations/post-m8-operating-points-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/m10-operating-point-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run development-only M10 operating-point study")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--temporal-config", type=Path, default=DEFAULT_TEMPORAL_CONFIG)
    parser.add_argument("--baseline-config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    parser.add_argument("--tree-config", type=Path, default=DEFAULT_TREE_CONFIG)
    parser.add_argument("--feature-dataset", type=Path, default=DEFAULT_FEATURE_DATASET)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--m6-report", type=Path, default=DEFAULT_M6_REPORT)
    parser.add_argument("--oof-dataset", type=Path, default=DEFAULT_OOF_DATASET)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    for path in (
        args.feature_dataset,
        args.candidate_manifest,
        args.m6_report,
        args.oof_dataset,
        args.analysis,
        args.report,
    ):
        _require_ignored_path(path)
    config = load_config(args.config)
    temporal_config = load_risk_temporal_validation_config(args.temporal_config)
    baseline_config = load_risk_baseline_config(args.baseline_config)
    tree_config = load_risk_tree_model_config(args.tree_config)
    feature_dataset = json.loads(args.feature_dataset.read_text(encoding="utf-8"))
    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    m6_report = json.loads(args.m6_report.read_text(encoding="utf-8"))
    dataset, evidence = reconstruct_development_oof(
        config,
        temporal_config,
        baseline_config,
        tree_config,
        feature_dataset,
        candidate_manifest,
        m6_report,
    )
    write_immutable_json(args.oof_dataset, dataset)
    analysis, report = analyze_operating_points(config, dataset, evidence)
    write_immutable_json(args.analysis, analysis)
    write_report(args.report, report)
    return {
        "passed": True,
        "oof_dataset": str(args.oof_dataset),
        "analysis": str(args.analysis),
        "report": str(args.report),
        "development_row_count": report["development_row_count"],
        "result_scope": report["result_scope"],
        "sealed_test_rows_used": 0,
        "m7_final_candidate_refit_performed": False,
        "m7_rerun_performed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M10 inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
