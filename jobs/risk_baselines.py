from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.modeling.baselines import (
    load_risk_baseline_config,
    run_risk_baselines,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/risk_baselines.v1.json")
DEFAULT_FEATURE_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_MODEL = Path(".tools/models/risk-logistic-model-v1/model.json")
DEFAULT_REPORT = Path("artifacts/m4-risk-baseline-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run leakage-safe M4 risk baselines")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--feature-dataset", type=Path, default=DEFAULT_FEATURE_DATASET)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    feature_dataset_path: Path,
    model_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (feature_dataset_path, model_path, report_path):
        _require_ignored_path(path)
    config = load_risk_baseline_config(config_path)
    feature_dataset = json.loads(feature_dataset_path.read_text(encoding="utf-8"))
    model, report = run_risk_baselines(config, feature_dataset)
    write_immutable_json(model_path, model)
    write_report(report_path, report)
    return {
        "passed": report["passed"],
        "model": str(model_path),
        "report": str(report_path),
        "row_counts": report["row_counts"],
        "sealed_test_features_or_outcomes_opened": False,
        "model_selection_performed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M4 generated inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(args.config, args.feature_dataset, args.model, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
