from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipelines.features.final_study_builder import write_immutable_json, write_report
from pipelines.intelligence.financial_nlp import (
    FinancialNlpIntelligenceConfig,
    assemble_intelligence_item,
    load_financial_nlp_intelligence_config,
    verify_historical_evidence,
)
from pipelines.news.types import NewsItem, TickerMatch

DEFAULT_CONFIG = Path("research/configs/financial_nlp_intelligence.v1.json")
DEFAULT_ANALYSIS = Path(".tools/evaluation/f8-financial-nlp-intelligence-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/f8-financial-nlp-intelligence-report.json")
TAIPEI = ZoneInfo("Asia/Taipei")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit the frozen F8 Financial NLP Intelligence product contract"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def run(config_path: Path, analysis_path: Path, report_path: Path) -> dict[str, object]:
    for path in (analysis_path, report_path):
        _require_local_output_path(path)
    config = load_financial_nlp_intelligence_config(config_path)
    repository_root = Path.cwd().resolve()
    evidence = verify_historical_evidence(config, repository_root=repository_root)
    records = _contract_routing_fixtures(config)

    sentiment_routes: dict[str, int] = {}
    event_routes: dict[str, int] = {}
    for record in records:
        sentiment_status = str(record["sentiment"]["status"])
        event_status = str(record["event_intelligence"]["status"])
        sentiment_routes[sentiment_status] = sentiment_routes.get(sentiment_status, 0) + 1
        event_routes[event_status] = event_routes.get(event_status, 0) + 1

    analysis_body: dict[str, object] = {
        "schema_version": config.analysis_version,
        "config_sha256": config.canonical_sha256,
        "historical_evidence": evidence,
        "historical_evidence_all_verified": all(row["passed"] for row in evidence),
        "controlled_fixture_count": len(records),
        "controlled_fixtures_are_performance_evaluation": False,
        "fixture_rows_persisted": False,
        "sentiment_route_counts": dict(sorted(sentiment_routes.items())),
        "event_route_counts": dict(sorted(event_routes.items())),
        "output_contract_fields": config.output_contract["required_fields"],
        "capability_matrix": config.product_capabilities,
        "english_model_version": config.english_model_version,
        "chinese_sentiment_policy": config.taiwan_sentiment["status"],
        "eland_status": config.eland["status"],
        "external_api_called": False,
        "model_downloaded": False,
        "model_inference_performed": False,
        "model_training_performed": False,
        "manual_annotation_performed": False,
        "manual_review_performed": False,
        "llm_called": False,
        "deployment_performed": False,
        "track_a_modified": False,
    }
    analysis = {**analysis_body, "sha256": _canonical_hash(analysis_body)}
    passed = bool(
        analysis["historical_evidence_all_verified"]
        and sentiment_routes == {"ABSTAIN": 2, "ELIGIBLE_NOT_SCORED": 1}
        and event_routes == {"ABSTAIN": 2, "SIGNAL": 1}
    )
    report = {
        "schema_version": config.report_version,
        "passed": passed,
        "analysis_sha256": analysis["sha256"],
        "config_sha256": config.canonical_sha256,
        "historical_evidence_all_verified": analysis["historical_evidence_all_verified"],
        "controlled_fixture_count": len(records),
        "controlled_fixtures_are_performance_evaluation": False,
        "sentiment_route_counts": analysis["sentiment_route_counts"],
        "event_route_counts": analysis["event_route_counts"],
        "english_model_version": config.english_model_version,
        "chinese_sentiment_policy": config.taiwan_sentiment["status"],
        "eland_status": config.eland["status"],
        "rows_or_private_text_persisted": False,
        "external_api_called": False,
        "model_downloaded": False,
        "model_inference_performed": False,
        "model_training_performed": False,
        "manual_annotation_or_review_performed": False,
        "llm_called": False,
        "deployment_performed": False,
    }
    write_immutable_json(analysis_path, analysis)
    write_report(report_path, report)
    return {
        "passed": passed,
        "analysis": str(analysis_path),
        "report": str(report_path),
        "analysis_sha256": analysis["sha256"],
        "historical_evidence_all_verified": analysis["historical_evidence_all_verified"],
        "controlled_fixture_count": len(records),
        "external_api_called": False,
        "model_inference_performed": False,
        "model_training_performed": False,
        "deployed": False,
    }


def _contract_routing_fixtures(
    config: FinancialNlpIntelligenceConfig,
) -> list[dict[str, object]]:
    fixtures = [
        (
            NewsItem(
                title="Company reports quarterly results",
                summary="Revenue increased during the quarter.",
                published_at=datetime(2024, 1, 2, 9, tzinfo=TAIPEI),
                source="controlled_fixture",
                source_type="contract_test",
                url="https://example.invalid/en-1",
                language="en",
                external_id="controlled-en-1",
            ),
            [],
        ),
        (
            NewsItem(
                title="公司公告月營收成長並取得重大訂單",
                summary="公開資訊觀測站重大訊息摘要",
                published_at=datetime(2024, 1, 2, 10, tzinfo=TAIPEI),
                source="controlled_fixture",
                source_type="official_announcement",
                url="https://example.invalid/zh-1",
                language="zh-TW",
                external_id="controlled-zh-1",
                explicit_tickers=("2330",),
                metadata={"company_name": "範例公司", "clause": "31", "fact_date": "1130102"},
            ),
            [TickerMatch("2330", 1.0, "official_company_code")],
        ),
        (
            NewsItem(
                title="依規定補充說明相關資訊",
                summary=None,
                published_at=datetime(2024, 1, 2, 11, tzinfo=TAIPEI),
                source="controlled_fixture",
                source_type="official_announcement",
                url="https://example.invalid/zh-2",
                language="zh-TW",
                external_id="controlled-zh-2",
            ),
            [],
        ),
    ]
    return [assemble_intelligence_item(config, item, matches) for item, matches in fixtures]


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _require_local_output_path(path: Path) -> None:
    root = Path.cwd().resolve()
    allowed = ((root / ".tools").resolve(), (root / "artifacts").resolve())
    if not any(path.resolve().is_relative_to(candidate) for candidate in allowed):
        raise ValueError("F8 outputs must stay in .tools/ or artifacts/")


def main() -> int:
    args = build_parser().parse_args()
    result = run(args.config, args.analysis, args.report)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
