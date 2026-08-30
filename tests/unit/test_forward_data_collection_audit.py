import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/forward_data_collection_audit.v1.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_forward_collection_audit_keeps_research_and_deployment_frozen() -> None:
    config = _config()
    assert config["decision"] == "AUDIT_COMPLETE_IMPLEMENTATION_NOT_READY"
    assert config["deployment_performed"] is False
    assert config["automatic_retraining"] is False
    assert config["track_a_changed"] is False
    assert config["track_b_model_changed"] is False
    assert config["f11b_2_unlocked"] is False


def test_official_event_sources_pass_but_scheduler_remains_blocked() -> None:
    config = _config()
    sources = config["sources"]
    assert isinstance(sources, list)
    assert {source["source_id"] for source in sources} == {
        "twse_openapi_daily_material",
        "tpex_openapi_daily_material",
    }
    assert all(source["probe_status"] == "PASS" for source in sources)
    assert all(source["timezone_aware"] is True for source in sources)
    assert all(source["raw_payload_persisted"] is False for source in sources)

    track_b = config["track_b_event_collection"]
    assert isinstance(track_b, dict)
    assert track_b["implementation_readiness"] == "NOT_READY"
    assert track_b["scheduler_deployed"] == "FAIL"
    assert track_b["raw_snapshot_integration"] == "FAIL"


def test_track_a_official_collection_cannot_bypass_feature_parity_gate() -> None:
    config = _config()
    track_a = config["track_a_market_collection"]
    assert isinstance(track_a, dict)
    assert track_a["allowed_role"] == "LINEAGE_AND_PARITY_EVIDENCE_ONLY"
    assert track_a["f7_external_validation_ready"] is False
    assert track_a["exact_feature_parity"] == "5_OF_23"
    assert track_a["serving_gates"] == "6_OF_9"
    assert track_a["f11b_2_status"] == "BLOCKED"


def test_forward_collection_never_implies_retraining_or_sentiment_truth() -> None:
    config = _config()
    policy = config["collection_policy"]
    assert isinstance(policy, dict)
    assert policy["collection_is_automatic_retraining"] is False
    assert policy["manual_sentiment_labels"] == "FORBIDDEN"
    assert policy["line_gas_changes"] == "FORBIDDEN"
    assert config["next_executable_unit"] == (
        "PRIVATE_FORWARD_EVENT_COLLECTION_RUNNER_IMPLEMENTATION"
    )
