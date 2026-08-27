from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.modeling.final_regressors import load_final_regression_config
from research.modeling.final_research_model import (
    freeze_final_research_model,
    load_final_model_freeze_config,
    write_f7_outputs,
)
from research.planning.final_study_protocol import load_final_study_config

DEFAULT_CONFIG = Path("research/configs/final_model_freeze.v1.json")
DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_REGRESSION_CONFIG = Path("research/configs/final_regression_models.v1.json")
DEFAULT_DATASET = Path(".tools/datasets/final-volatility-surprise-dataset-v1/dataset.json")
DEFAULT_OOF = Path(".tools/evaluation/f5-final-regression-oof-v1/predictions.json")
DEFAULT_F6_ANALYSIS = Path(".tools/evaluation/f6-final-ranking-robustness-v1/analysis.json")
DEFAULT_ARTIFACT = Path(".tools/models/f7-final-ridge-research-v1/model.json")
DEFAULT_REPORT = Path("artifacts/f7-final-research-model-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze the final F7 research model")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--regression-config", type=Path, default=DEFAULT_REGRESSION_CONFIG)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--oof", type=Path, default=DEFAULT_OOF)
    parser.add_argument("--f6-analysis", type=Path, default=DEFAULT_F6_ANALYSIS)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    protocol_path: Path,
    regression_config_path: Path,
    dataset_path: Path,
    oof_path: Path,
    f6_analysis_path: Path,
    artifact_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (dataset_path, oof_path, f6_analysis_path, artifact_path, report_path):
        _require_local_data_path(path)
    config = load_final_model_freeze_config(config_path)
    protocol = load_final_study_config(protocol_path)
    regression_config = load_final_regression_config(regression_config_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    oof = json.loads(oof_path.read_text(encoding="utf-8"))
    f6_analysis = json.loads(f6_analysis_path.read_text(encoding="utf-8"))
    artifact, report = freeze_final_research_model(
        config, protocol, regression_config, dataset, oof, f6_analysis
    )
    write_f7_outputs(artifact_path, report_path, artifact, report)
    return {
        "passed": report["passed"],
        "artifact": str(artifact_path),
        "report": str(report_path),
        "artifact_sha256": report["artifact_sha256"],
        "selected_model": report["selected_model"],
        "selected_hyperparameters": report["selected_hyperparameters"],
        "training_row_count": report["training_row_count"],
        "final_model_selected": True,
        "model_artifact_persisted": True,
        "deployed": False,
        "m7_rerun_performed": False,
    }


def _require_local_data_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F7 inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(
        args.config,
        args.protocol,
        args.regression_config,
        args.dataset,
        args.oof,
        args.f6_analysis,
        args.artifact,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
