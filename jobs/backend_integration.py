from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.main import app
from backend.app.schemas.research import VolatilitySurprisePredictionRequest
from backend.app.services.research_prediction import ResearchPredictionService
from pipelines.features.final_study_builder import write_immutable_json, write_report
from pipelines.features.risk_builder import FEATURE_NAMES
from pipelines.intelligence.financial_nlp import load_financial_nlp_intelligence_config
from research.planning.backend_integration import (
    canonical_f10_config_sha256,
    load_backend_integration_config,
)

DEFAULT_CONFIG = Path("research/configs/backend_integration.v1.json")
DEFAULT_ARTIFACT = Path(".tools/models/f7-final-ridge-research-v1/model.json")
DEFAULT_ANALYSIS = Path(".tools/evaluation/f10-backend-integration-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/f10-backend-integration-report.json")
TAIPEI = ZoneInfo("Asia/Taipei")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit the frozen F10 backend integration")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(
    config_path: Path,
    artifact_path: Path,
    analysis_path: Path,
    report_path: Path,
) -> dict[str, object]:
    for path in (analysis_path, report_path):
        _require_local_output_path(path)
    config = load_backend_integration_config(config_path)
    f8_config_path = _resolve_repository_path(config.f8_config_path)
    f8_config = load_financial_nlp_intelligence_config(f8_config_path)
    if f8_config.canonical_sha256 != config.f8_config_sha256:
        raise ValueError("F10/F8 configuration lineage mismatch")
    service = ResearchPredictionService.from_path(config, artifact_path)
    controlled_request = VolatilitySurprisePredictionRequest(
        ticker="2330",
        as_of_date=date(2026, 8, 28),
        information_cutoff=datetime(2026, 8, 28, 13, 30, tzinfo=TAIPEI),
        features={name: 0.0 for name in FEATURE_NAMES},
    )
    prediction = service.predict(controlled_request)
    routes = _registered_paths()
    required_routes = {config.prediction_endpoint, config.intelligence_endpoint}
    route_audit = {
        path: path in routes for path in sorted(required_routes)
    }
    analysis_body: dict[str, object] = {
        "schema_version": "f10-backend-integration-analysis-v1",
        "config_sha256": canonical_f10_config_sha256(config),
        "f7_artifact_sha256": service.artifact["sha256"],
        "f8_config_sha256": f8_config.canonical_sha256,
        "route_audit": route_audit,
        "required_routes_all_registered": all(route_audit.values()),
        "controlled_prediction_contract_valid": (
            prediction.schema_version == config.prediction_response_version
            and prediction.artifact_sha256 == config.f7_artifact_sha256
            and prediction.claim_boundary.research_signal_only
            and not prediction.claim_boundary.price_direction_forecast
        ),
        "controlled_prediction_is_performance_evaluation": False,
        "controlled_features_or_prediction_persisted": False,
        "intelligence_database_only": config.intelligence_retrieval["database_only"],
        "intelligence_external_fetch_on_request": False,
        "intelligence_model_inference_on_request": False,
        "intelligence_llm_on_request": False,
        "external_api_called": False,
        "model_training_performed": False,
        "gas_modified": False,
        "deployment_performed": False,
        "m7_rerun_performed": False,
    }
    analysis = {**analysis_body, "sha256": _canonical_hash(analysis_body)}
    passed = bool(
        analysis["required_routes_all_registered"]
        and analysis["controlled_prediction_contract_valid"]
        and analysis["intelligence_database_only"]
    )
    report = {
        "schema_version": "f10-backend-integration-report-v1",
        "passed": passed,
        "analysis_sha256": analysis["sha256"],
        "config_sha256": analysis["config_sha256"],
        "f7_artifact_sha256": analysis["f7_artifact_sha256"],
        "f8_config_sha256": analysis["f8_config_sha256"],
        "route_audit": route_audit,
        "controlled_prediction_contract_valid": analysis[
            "controlled_prediction_contract_valid"
        ],
        "controlled_prediction_is_performance_evaluation": False,
        "raw_features_or_prediction_persisted": False,
        "external_api_called": False,
        "model_training_performed": False,
        "gas_modified": False,
        "deployment_performed": False,
        "m7_rerun_performed": False,
    }
    write_immutable_json(analysis_path, analysis)
    write_report(report_path, report)
    return {
        "passed": passed,
        "analysis": str(analysis_path),
        "report": str(report_path),
        "analysis_sha256": analysis["sha256"],
        "routes_registered": all(route_audit.values()),
        "controlled_prediction_contract_valid": analysis[
            "controlled_prediction_contract_valid"
        ],
        "external_api_called": False,
        "model_training_performed": False,
        "deployed": False,
    }


def _resolve_repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def _registered_paths() -> set[str]:
    paths: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.add(path)
        included = getattr(route, "original_router", None)
        for nested in getattr(included, "routes", ()):
            nested_path = getattr(nested, "path", None)
            if isinstance(nested_path, str):
                paths.add(nested_path)
    return paths


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _require_local_output_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F10 outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(args.config, args.artifact, args.analysis, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
