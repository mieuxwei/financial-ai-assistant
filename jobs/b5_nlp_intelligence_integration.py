from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipelines.features.final_study_builder import write_immutable_json, write_report
from pipelines.intelligence.b5_integration import (
    assemble_b5_intelligence,
    load_b5_intelligence_config,
)
from pipelines.intelligence.financial_nlp import load_financial_nlp_intelligence_config

DEFAULT_CONFIG = Path("research/configs/b5_nlp_intelligence_integration.v1.json")
DEFAULT_F8_CONFIG = Path("research/configs/financial_nlp_intelligence.v1.json")
DEFAULT_B4_RESULT = Path("research/evaluation/b4_market_reaction_validation_result.md")
DEFAULT_ANALYSIS = Path(".tools/evaluation/b5-nlp-intelligence-integration-v1/analysis.json")
DEFAULT_REPORT = Path("artifacts/b5-nlp-intelligence-integration-report.json")
TAIPEI = ZoneInfo("Asia/Taipei")


def run(
    config_path: Path = DEFAULT_CONFIG,
    analysis_path: Path = DEFAULT_ANALYSIS,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, object]:
    config = load_b5_intelligence_config(config_path)
    f8 = load_financial_nlp_intelligence_config(DEFAULT_F8_CONFIG)
    checks = {
        "f8_lineage": config.f8_config_canonical_sha256 == f8.canonical_sha256,
        "b4_lineage": config.b4_result_sha256
        == hashlib.sha256(DEFAULT_B4_RESULT.read_bytes()).hexdigest(),
        "maturity_preserved": config.market_reaction["maturity"] == "AUTOMATED_SIGNAL_ONLY",
        "direction_abstains": config.market_reaction["direction_status"]
        == "ABSTAIN_DIRECTION_NOT_SUPPORTED",
        "chinese_sentiment_abstains": config.chinese_linguistic_sentiment["reason"]
        == "CHINESE_SENTIMENT_NOT_VALIDATED",
        "provider_call_on_request": config.source_boundary["provider_call_on_request"] is False,
    }
    fixture = assemble_b5_intelligence(
        config,
        source="controlled_b5_fixture",
        source_type="CONTROLLED_RESEARCH_FIXTURE",
        published_at=datetime(2025, 6, 2, 18, tzinfo=TAIPEI),
        language="zh-TW",
        metadata={},
        requested_cutoff=datetime(2025, 6, 3, 9, tzinfo=TAIPEI),
    )
    analysis_body = {
        "contract_version": config.contract_version,
        "config_sha256": config.canonical_sha256,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "fixture_is_live_data": False,
        "fixture_market_reaction_status": fixture["market_reaction"]["status"],
        "fixture_chinese_sentiment_status": fixture["linguistic_sentiment"]["status"],
        "private_payload_persisted": False,
        "provider_calls": False,
        "model_inference": False,
        "model_training": False,
        "llm_calls": False,
        "deployment": False,
        "track_a_modified": False,
        "gas_line_modified": False,
    }
    analysis_sha = hashlib.sha256(
        json.dumps(analysis_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    analysis = {**analysis_body, "sha256": analysis_sha}
    report = {
        "report_version": "b5-nlp-intelligence-integration-report-v1",
        "passed": analysis["all_checks_passed"],
        "analysis_sha256": analysis_sha,
        "config_sha256": config.canonical_sha256,
        "market_reaction_maturity": "AUTOMATED_SIGNAL_ONLY",
        "chinese_sentiment": "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED",
        "direction_status": "ABSTAIN_DIRECTION_NOT_SUPPORTED",
        "request_time_provider_calls": False,
        "model_training": False,
        "deployment": False,
        "next_executable_unit": "F11B_CONTROLLED_LINE_FINANCIAL_AI_INTEGRATION",
    }
    write_immutable_json(analysis_path, analysis)
    write_report(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit B5 NLP Intelligence Integration")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.analysis, args.report), sort_keys=True))


if __name__ == "__main__":
    main()
