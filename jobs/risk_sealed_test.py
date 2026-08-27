from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.features.risk_builder import load_risk_feature_config
from research.evaluation.sealed_risk_test import (
    claim_sealed_test_opening,
    completion_record,
    evaluate_sealed_test,
    load_risk_sealed_test_config,
    verify_sealed_test_preflight,
    write_immutable_json,
    write_report,
)
from research.modeling.baselines import load_risk_baseline_config
from research.modeling.tree_models import load_risk_tree_model_config
from research.risk_labels.protocol import load_risk_label_config

DEFAULT_CONFIG = Path("research/configs/risk_sealed_test.v1.json")
DEFAULT_LABEL_CONFIG = Path("research/configs/next_session_volatility_risk.v1.json")
DEFAULT_FEATURE_CONFIG = Path("research/configs/risk_features.v1.json")
DEFAULT_BASELINE_CONFIG = Path("research/configs/risk_baselines.v1.json")
DEFAULT_TREE_CONFIG = Path("research/configs/risk_tree_models.v1.json")
DEFAULT_PRETEST_DATASET = Path(".tools/datasets/risk-feature-dataset-v1/dataset.json")
DEFAULT_CANDIDATE_MANIFEST = Path(".tools/models/risk-final-candidate-v1/manifest.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_THRESHOLD = Path(".tools/datasets/next-session-volatility-risk-v1/threshold.json")
DEFAULT_OPENING_INTENT = Path(
    ".tools/evaluations/risk-sealed-test-v1/opening-intent.json"
)
DEFAULT_EVALUATION = Path(".tools/evaluations/risk-sealed-test-v1/evaluation.json")
DEFAULT_COMPLETION = Path(".tools/evaluations/risk-sealed-test-v1/completion.json")
DEFAULT_REPORT = Path("artifacts/m7-risk-sealed-test-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open and evaluate the frozen risk sealed test exactly once"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--label-config", type=Path, default=DEFAULT_LABEL_CONFIG)
    parser.add_argument("--feature-config", type=Path, default=DEFAULT_FEATURE_CONFIG)
    parser.add_argument("--baseline-config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    parser.add_argument("--tree-config", type=Path, default=DEFAULT_TREE_CONFIG)
    parser.add_argument("--pretest-dataset", type=Path, default=DEFAULT_PRETEST_DATASET)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--market-dataset", type=Path, default=DEFAULT_MARKET_DATASET)
    parser.add_argument("--threshold", type=Path, default=DEFAULT_THRESHOLD)
    parser.add_argument("--opening-intent", type=Path, default=DEFAULT_OPENING_INTENT)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--completion", type=Path, default=DEFAULT_COMPLETION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    for path in (
        args.pretest_dataset,
        args.candidate_manifest,
        args.market_dataset,
        args.threshold,
        args.opening_intent,
        args.evaluation,
        args.completion,
        args.report,
    ):
        _require_ignored_path(path)
    for path in (args.opening_intent, args.evaluation, args.completion):
        if path.exists():
            raise FileExistsError(
                f"sealed test was already claimed or evaluated; repeat refused: {path}"
            )

    config = load_risk_sealed_test_config(args.config)
    label_config = load_risk_label_config(args.label_config)
    feature_config = load_risk_feature_config(args.feature_config)
    baseline_config = load_risk_baseline_config(args.baseline_config)
    tree_config = load_risk_tree_model_config(args.tree_config)
    pretest_dataset = json.loads(args.pretest_dataset.read_text(encoding="utf-8"))
    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    verify_sealed_test_preflight(
        config,
        candidate_manifest,
        label_config,
        feature_config,
        baseline_config,
        tree_config,
        pretest_dataset,
    )

    opening_intent = claim_sealed_test_opening(args.opening_intent, config)
    market_dataset = json.loads(args.market_dataset.read_text(encoding="utf-8"))
    threshold_artifact = json.loads(args.threshold.read_text(encoding="utf-8"))
    evaluation, report = evaluate_sealed_test(
        config,
        candidate_manifest,
        market_dataset,
        threshold_artifact,
        label_config,
        feature_config,
        baseline_config,
        tree_config,
        pretest_dataset,
        opening_intent,
    )
    write_immutable_json(args.evaluation, evaluation)
    write_report(args.report, report)
    completion = completion_record(config, opening_intent, evaluation, report)
    write_immutable_json(args.completion, completion)
    return {
        "passed": report["passed"],
        "evaluation_sequence": 1,
        "evaluation": str(args.evaluation),
        "completion": str(args.completion),
        "report": str(args.report),
        "row_count": report["row_count"],
        "selected_model": report["selected_model"],
        "selected_calibration": report["selected_calibration"],
        "selected_threshold": report["selected_threshold"],
        "repeat_evaluation_allowed": False,
    }


def _require_ignored_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("M7 sensitive inputs and outputs must stay in .tools/ or artifacts/")


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
