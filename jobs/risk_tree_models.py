from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.modeling.tree_models import (
    load_risk_tree_model_config,
    run_risk_tree_models,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/risk_tree_models.v1.json")
DEFAULT_FEATURE_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_MANIFEST = Path(".tools/models/risk-tree-models-v1/evaluation-manifest.json")
DEFAULT_REPORT = Path("artifacts/m5-risk-tree-model-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run leakage-safe M5 risk tree models")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--feature-dataset", type=Path, default=DEFAULT_FEATURE_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    feature_dataset_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (feature_dataset_path, manifest_path, report_path):
        _require_ignored_path(path)
    config = load_risk_tree_model_config(config_path)
    feature_dataset = json.loads(feature_dataset_path.read_text(encoding="utf-8"))
    manifest, report = run_risk_tree_models(config, feature_dataset)
    write_immutable_json(manifest_path, manifest)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "manifest": str(manifest_path),
        "report": str(report_path),
        "row_counts": report["row_counts"],
        "models": sorted(report["metrics"]),
        "sealed_test_features_or_outcomes_opened": False,
        "model_selection_performed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M5 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(args.config, args.feature_dataset, args.manifest, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
