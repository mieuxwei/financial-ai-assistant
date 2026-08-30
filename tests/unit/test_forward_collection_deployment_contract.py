import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/forward_collection_deployment.v1.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_deployment_status_does_not_claim_external_resources_exist() -> None:
    config = _config()
    assert config["success_state"] == "FORWARD_COLLECTION_READY_FOR_MANUAL_DEPLOYMENT"
    assert config["implemented"] is True
    assert config["deployed"] is False
    assert config["first_smoke_verified"] is False
    assert config["scheduler_enabled"] is False
    storage = config["storage"]
    assert isinstance(storage, dict)
    assert storage["bucket_created"] is False
    assert storage["private_access_verified"] is False
    assert storage["public_url"] is None


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
