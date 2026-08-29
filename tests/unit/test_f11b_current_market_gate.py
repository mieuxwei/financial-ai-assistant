from pathlib import Path

import pytest

from research.evaluation.f11b_current_market_gate import (
    GATE_IDS,
    CurrentMarketGateAudit,
    load_current_market_gate_audit,
)

CONFIG = Path("research/configs/f11b_current_market_gate_audit.v1.json")


def test_current_market_gate_is_complete_but_blocks_integration() -> None:
    audit = load_current_market_gate_audit(CONFIG)

    assert tuple(gate.id for gate in audit.gates) == GATE_IDS
    assert audit.gate_summary.required == 9
    assert audit.gate_summary.passed == 2
    assert audit.gate_summary.blocked == 7
    assert audit.gate_summary.all_passed is False
    assert audit.f11b_2_integration_allowed is False
    assert audit.f11b_2_started is False
    assert len(audit.canonical_sha256) == 64


def test_source_and_real_missing_session_findings_are_preserved() -> None:
    audit = load_current_market_gate_audit(CONFIG)

    assert audit.stock_source["classification"] == "CONDITIONAL_BLOCKED_FOR_CURRENT_SERVING"
    assert audit.stock_source["formal_endpoint_documentation_verified"] is False
    assert audit.stock_source["tickers_complete_for_latest_35_sessions"] == 9
    assert audit.stock_source["tickers_missing_latest_35_session"] == ["0050"]
    assert audit.benchmark_source["classification"] == "ACCEPT_RESEARCH_CURRENT"
    assert audit.benchmark_source["probe_last_session"] == "2026-08-28"
    assert audit.adjusted_ohlcv_alternative_probe["dataset"] == "TaiwanStockPriceAdj"
    assert audit.adjusted_ohlcv_alternative_probe["http_status"] == 400
    assert audit.adjusted_ohlcv_alternative_probe["entitled_in_current_environment"] is False


def test_gate_contract_rejects_bypass_or_count_drift() -> None:
    payload = load_current_market_gate_audit(CONFIG).model_dump(mode="json")
    payload["f11b_2_integration_allowed"] = True
    with pytest.raises(ValueError, match="cannot bypass"):
        CurrentMarketGateAudit.model_validate(payload)

    payload = load_current_market_gate_audit(CONFIG).model_dump(mode="json")
    payload["gate_summary"]["passed"] = 9
    payload["gate_summary"]["blocked"] = 0
    payload["gate_summary"]["all_passed"] = True
    with pytest.raises(ValueError, match="counts drifted"):
        CurrentMarketGateAudit.model_validate(payload)


def test_gate_audit_contains_no_raw_prices_or_secrets() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    assert '"prices_published": false' in text
    assert '"raw_provider_payload_stored": false' in text
    for forbidden in ("API_KEY=", "Bearer ", "LINE_ACCESS_TOKEN", "F11B_SERVICE_SECRET"):
        assert forbidden not in text
