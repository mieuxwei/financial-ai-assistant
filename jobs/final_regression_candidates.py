from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from pipelines.features.final_study_builder import write_report
from research.modeling.final_regressors import (
    MODEL_NAMES,
    canonical_f4_config_sha256,
    load_final_regression_config,
    verify_f4_contract,
)
from research.planning.final_study_protocol import (
    canonical_config_sha256,
    load_final_study_config,
)

DEFAULT_CONFIG = Path("research/configs/final_regression_models.v1.json")
DEFAULT_PROTOCOL = Path("research/configs/final_volatility_surprise_study.v1.json")
DEFAULT_REPORT = Path("artifacts/f4-final-regression-candidate-contract.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the frozen F4 regression candidates")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def verify(config_path: Path, protocol_path: Path, report_path: Path) -> dict[str, object]:
    _require_report_path(report_path)
    config = load_final_regression_config(config_path)
    protocol = load_final_study_config(protocol_path)
    verify_f4_contract(config, protocol)
    candidate_counts = {
        model.name: _grid_size(model.hyperparameters) for model in protocol.models
    }
    report = {
        "report_version": "f4-final-regression-candidate-contract-v1",
        "passed": True,
        "f1_protocol_config_sha256": canonical_config_sha256(protocol),
        "f4_config_sha256": canonical_f4_config_sha256(config),
        "model_names": list(MODEL_NAMES),
        "candidate_parameter_counts": candidate_counts,
        "total_parameterized_candidates": sum(candidate_counts.values()),
        "target_version": config.target_version,
        "target_transform": config.target_transform,
        "inverse_transform": config.inverse_transform,
        "feature_count": len(protocol.features.fixed_feature_names),
        "validation_or_outer_rows_used_for_fitting": False,
        "hyperparameter_selection_performed": False,
        "historical_outer_evaluation_run": False,
        "model_artifact_persisted": False,
        "models_trained": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    write_report(report_path, report)
    return report


def _grid_size(grid: dict[str, object]) -> int:
    if not grid:
        return 1
    values = []
    for name in sorted(grid):
        choices = grid[name]
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"F1 candidate grid is invalid: {name}")
        values.append(choices)
    return sum(1 for _ in itertools.product(*values))


def _require_report_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = (root / "artifacts").resolve()
    if not path.resolve().is_relative_to(allowed):
        raise ValueError("F4 generated report must stay in artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    report = verify(args.config, args.protocol, args.report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
