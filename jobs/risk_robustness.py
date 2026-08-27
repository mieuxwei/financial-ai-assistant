from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.risk_robustness import (
    analyze_risk_robustness,
    load_risk_robustness_config,
    verify_m7_chain,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/risk_robustness.v1.json")
DEFAULT_EVALUATION = Path(".tools/evaluations/risk-sealed-test-v1/evaluation.json")
DEFAULT_OPENING = Path(".tools/evaluations/risk-sealed-test-v1/opening-intent.json")
DEFAULT_COMPLETION = Path(".tools/evaluations/risk-sealed-test-v1/completion.json")
DEFAULT_M7_REPORT = Path("artifacts/m7-risk-sealed-test-report.json")
DEFAULT_PRETEST_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_ANALYSIS = Path(".tools/evaluations/risk-robustness-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/m8-risk-robustness-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze the existing M7 evaluation without rerun")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--opening", type=Path, default=DEFAULT_OPENING)
    parser.add_argument("--completion", type=Path, default=DEFAULT_COMPLETION)
    parser.add_argument("--m7-report", type=Path, default=DEFAULT_M7_REPORT)
    parser.add_argument("--pretest-dataset", type=Path, default=DEFAULT_PRETEST_DATASET)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    for path in (
        args.evaluation,
        args.opening,
        args.completion,
        args.m7_report,
        args.pretest_dataset,
        args.analysis,
        args.report,
    ):
        _require_ignored_path(path)
    config = load_risk_robustness_config(args.config)
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    opening = json.loads(args.opening.read_text(encoding="utf-8"))
    completion = json.loads(args.completion.read_text(encoding="utf-8"))
    m7_report = json.loads(args.m7_report.read_text(encoding="utf-8"))
    pretest_dataset = json.loads(args.pretest_dataset.read_text(encoding="utf-8"))
    verify_m7_chain(
        config,
        evaluation,
        opening,
        completion,
        m7_report,
        pretest_dataset,
    )
    analysis, report = analyze_risk_robustness(config, evaluation, pretest_dataset)
    write_immutable_json(args.analysis, analysis)
    write_report(args.report, report)
    return {
        "passed": report["passed"],
        "analysis": str(args.analysis),
        "report": str(args.report),
        "row_count": report["row_count"],
        "m7_evaluation_sequence": 1,
        "m7_rerun_performed": False,
        "model_or_threshold_selection_performed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M8 sensitive inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
