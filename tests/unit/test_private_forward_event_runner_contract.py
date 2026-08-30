import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/private_forward_event_runner.v1.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_runner_result_is_local_private_and_not_deployed() -> None:
    config = _config()
    assert config["decision"] == "RUNNER_IMPLEMENTATION_COMPLETE_NOT_DEPLOYED"
    assert config["sources"] == [
        "twse_openapi_daily_material",
        "tpex_openapi_daily_material",
    ]
    storage = config["private_storage"]
    safety = config["safety"]
    assert isinstance(storage, dict)
    assert isinstance(safety, dict)
    assert storage["git_ignored"] is True
    assert storage["raw_before_parse"] is True
    assert storage["public_payload_allowed"] is False
    assert safety["scheduler_deployed"] is False
    assert safety["live_collection_executed_in_this_unit"] is False
    assert safety["automatic_retraining"] is False


def test_runner_contract_preserves_research_and_product_freezes() -> None:
    config = _config()
    safety = config["safety"]
    assert isinstance(safety, dict)
    assert safety["gas_or_line_modified"] is False
    assert safety["track_a_or_b_model_modified"] is False
    assert safety["f11b_2_unlocked"] is False
    assert config["next_executable_unit"] == (
        "PRIVATE_FORWARD_EVENT_COLLECTION_DEPLOYMENT_CONFIGURATION"
    )
