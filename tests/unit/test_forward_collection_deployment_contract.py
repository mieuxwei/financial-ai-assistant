import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/forward_collection_deployment.v1.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_deployment_status_records_verified_external_resources() -> None:
    config = _config()
    assert config["success_state"] == "FORWARD_COLLECTION_DEPLOYED_AND_SMOKE_VERIFIED"
    assert config["implemented"] is True
    assert config["deployed"] is True
    assert config["first_smoke_verified"] is True
    assert config["scheduler_enabled"] is True
    storage = config["storage"]
    assert isinstance(storage, dict)
    assert storage["bucket_created"] is True
    assert storage["private_access_verified"] is True
    assert storage["public_url"] is None


def test_live_smoke_and_remote_idempotency_are_frozen() -> None:
    smoke = _config()["smoke_test"]
    assert isinstance(smoke, dict)
    assert smoke["twse"] == {"status": "SUCCESS", "row_count": 7}
    assert smoke["tpex"] == {"status": "SUCCESS", "row_count": 5}
    assert smoke["same_run_id_live_idempotency"] == (
        "VERIFIED_REUSED_REMOTE_MANIFEST_TRUE"
    )
    assert smoke["provider_recalled_on_second_run"] is False
    assert smoke["schema_drift_live"] is False


def test_deployment_contract_keeps_cost_and_research_boundaries() -> None:
    config = _config()
    cost = config["cost_boundary"]
    research = config["research_boundary"]
    assert isinstance(cost, dict)
    assert isinstance(research, dict)
    assert cost["fixed_monthly_plan_enabled"] is False
    assert cost["zero_cost_guaranteed"] is False
    assert cost["stop_before_paid_upgrade"] is True
    assert research["automatic_retraining"] is False
    assert research["model_executed"] is False
    assert research["additional_provider_used"] is False
    assert research["gas_or_line_changed"] is False
    assert research["f11b_2_unlocked"] is False
