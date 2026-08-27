from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.modeling.final_regressors import load_final_regression_config
from research.modeling.final_temporal_evaluation import (
    load_final_temporal_evaluation_config,
    run_nested_temporal_evaluation,
    write_f5_outputs,
)
from research.planning.final_study_protocol import load_final_study_config

DEFAULT_CONFIG = Path("research/configs/final_nested_temporal_evaluation.v1.json")
DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_REGRESSION_CONFIG = Path("research/configs/final_regression_models.v1.json")
DEFAULT_DATASET = Path(".tools/datasets/final-volatility-surprise-dataset-v1/dataset.json")
DEFAULT_OOF = Path(".tools/evaluation/f5-final-regression-oof-v1/predictions.json")
DEFAULT_REPORT = Path("artifacts/f5-final-nested-temporal-evaluation-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the frozen F5 nested temporal evaluation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--regression-config", type=Path, default=DEFAULT_REGRESSION_CONFIG)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--oof", type=Path, default=DEFAULT_OOF)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    protocol_path: Path,
    regression_config_path: Path,
    dataset_path: Path,
    oof_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (dataset_path, oof_path, report_path):
        _require_local_data_path(path)
    config = load_final_temporal_evaluation_config(config_path)
    protocol = load_final_study_config(protocol_path)
    regression_config = load_final_regression_config(regression_config_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    oof_dataset, report = run_nested_temporal_evaluation(
        config,
        protocol,
        regression_config,
        dataset,
    )
    write_f5_outputs(oof_path, report_path, oof_dataset, report)
    return {
        "passed": report["passed"],
        "oof": str(oof_path),
        "report": str(report_path),
        "oof_dataset_sha256": report["oof_dataset_sha256"],
        "outer_fold_count": report["outer_fold_count"],
        "model_count": report["model_count"],
        "oof_row_count": report["oof_row_count"],
        "final_model_selected": False,
        "f6_analysis_performed": False,
        "model_artifact_persisted": False,
    }


def _require_local_data_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F5 inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(
        args.config,
        args.protocol,
        args.regression_config,
        args.dataset,
        args.oof,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
