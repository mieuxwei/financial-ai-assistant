from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.conditional_risk import (
    analyze_conditional_risk,
    load_config,
    write_immutable_json,
    write_report,
)

DEFAULT_CONFIG = Path("research/configs/post_m8_conditional_risk.v1.json")
DEFAULT_EVALUATION = Path(".tools/evaluations/risk-sealed-test-v1/evaluation.json")
DEFAULT_M8_ANALYSIS = Path(".tools/evaluations/risk-robustness-v1/analysis.json")
DEFAULT_ANALYSIS = Path(".tools/evaluations/post-m8-conditional-risk-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/m9-conditional-risk-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run analysis-only M9 conditional-risk study")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--m8-analysis", type=Path, default=DEFAULT_M8_ANALYSIS)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    for path in (args.evaluation, args.m8_analysis, args.analysis, args.report):
        _require_ignored_path(path)
    config = load_config(args.config)
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    m8_analysis = json.loads(args.m8_analysis.read_text(encoding="utf-8"))
    analysis, report = analyze_conditional_risk(config, evaluation, m8_analysis)
    write_immutable_json(args.analysis, analysis)
    write_report(args.report, report)
    return {
        "passed": True,
        "analysis": str(args.analysis),
        "report": str(args.report),
        "m7_prediction_count": report["m7_prediction_count"],
        "historical_threshold": report["historical_threshold"],
        "m7_rerun_performed": False,
        "m8_rerun_performed": False,
        "model_refit_performed": False,
        "threshold_change_performed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M9 historical inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
