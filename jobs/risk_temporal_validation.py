from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.modeling.baselines import load_risk_baseline_config
from research.modeling.temporal_validation import (
    load_risk_temporal_validation_config,
    run_temporal_validation,
    write_immutable_json,
    write_report,
)
from research.modeling.tree_models import load_risk_tree_model_config

DEFAULT_CONFIG = Path("research/configs/risk_temporal_validation.v1.json")
DEFAULT_BASELINE_CONFIG = Path("research/configs/risk_baselines.v1.json")
DEFAULT_TREE_CONFIG = Path("research/configs/risk_tree_models.v1.json")
DEFAULT_FEATURE_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_MANIFEST = Path(".tools/models/risk-final-candidate-v1/manifest.json")
DEFAULT_REPORT = Path("artifacts/m6-risk-temporal-validation-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run leakage-safe M6 temporal validation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--baseline-config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    parser.add_argument("--tree-config", type=Path, default=DEFAULT_TREE_CONFIG)
    parser.add_argument("--feature-dataset", type=Path, default=DEFAULT_FEATURE_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    baseline_config_path: Path,
    tree_config_path: Path,
    feature_dataset_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (feature_dataset_path, manifest_path, report_path):
        _require_ignored_path(path)
    config = load_risk_temporal_validation_config(config_path)
    baseline_config = load_risk_baseline_config(baseline_config_path)
    tree_config = load_risk_tree_model_config(tree_config_path)
    feature_dataset = json.loads(feature_dataset_path.read_text(encoding="utf-8"))
    manifest, report = run_temporal_validation(
        config, feature_dataset, baseline_config, tree_config
    )
    write_immutable_json(manifest_path, manifest)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "manifest": str(manifest_path),
        "report": str(report_path),
        "selected_model": report["selected_model"],
        "selected_calibration": report["selected_calibration"],
        "selected_threshold": report["selected_threshold"],
        "sealed_test_features_or_outcomes_opened": False,
        "sealed_test_evaluations": 0,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M6 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(
        args.config,
        args.baseline_config,
        args.tree_config,
        args.feature_dataset,
        args.manifest,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
