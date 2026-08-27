from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.final_ranking_robustness import (
    analyze_final_ranking_robustness,
    load_final_ranking_robustness_config,
    write_f6_outputs,
)
from research.modeling.final_temporal_evaluation import (
    load_final_temporal_evaluation_config,
)
from research.planning.final_study_protocol import load_final_study_config

DEFAULT_CONFIG = Path("research/configs/final_ranking_robustness.v1.json")
DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_F5_CONFIG = Path("research/configs/final_nested_temporal_evaluation.v1.json")
DEFAULT_DATASET = Path(".tools/datasets/final-volatility-surprise-dataset-v1/dataset.json")
DEFAULT_OOF = Path(".tools/evaluation/f5-final-regression-oof-v1/predictions.json")
DEFAULT_ANALYSIS = Path(".tools/evaluation/f6-final-ranking-robustness-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/f6-final-ranking-robustness-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze frozen F5 OOF ranking robustness")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--f5-config", type=Path, default=DEFAULT_F5_CONFIG)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--oof", type=Path, default=DEFAULT_OOF)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    protocol_path: Path,
    f5_config_path: Path,
    dataset_path: Path,
    oof_path: Path,
    analysis_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (dataset_path, oof_path, analysis_path, report_path):
        _require_local_data_path(path)
    config = load_final_ranking_robustness_config(config_path)
    protocol = load_final_study_config(protocol_path)
    f5_config = load_final_temporal_evaluation_config(f5_config_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    oof = json.loads(oof_path.read_text(encoding="utf-8"))
    analysis, report = analyze_final_ranking_robustness(
        config, protocol, f5_config, dataset, oof
    )
    write_f6_outputs(analysis_path, report_path, analysis, report)
    return {
        "passed": report["passed"],
        "analysis": str(analysis_path),
        "report": str(report_path),
        "analysis_sha256": report["analysis_sha256"],
        "unique_evaluation_row_count": report["unique_evaluation_row_count"],
        "oof_prediction_row_count": report["oof_prediction_row_count"],
        "bootstrap_replicates": report["cluster_bootstrap"]["replicates_requested"],
        "final_model_selected": False,
        "model_artifact_persisted": False,
        "m7_rerun_performed": False,
    }


def _require_local_data_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F6 inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(
        args.config,
        args.protocol,
        args.f5_config,
        args.dataset,
        args.oof,
        args.analysis,
        args.report,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
