import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from research.planning.backend_integration import (
    canonical_f10_config_sha256,
    load_backend_integration_config,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/backend_integration.v1.json"


def test_f10_config_freezes_lineage_claims_and_no_side_effect_boundary() -> None:
    config = load_backend_integration_config(CONFIG_PATH)

    assert config.f7_artifact_sha256 == (
        "279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de"
    )
    assert config.f8_config_sha256 == (
        "de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4"
    )
    assert config.intelligence_retrieval["database_only"] is True
    assert config.intelligence_retrieval["external_fetch_on_request"] is False
    assert config.intelligence_retrieval["model_inference_on_request"] is False
    assert config.claim_boundary["research_signal_only"] is True
    assert config.claim_boundary["price_direction_forecast"] is False
    assert config.modify_gas_in_f10 is False
    assert config.model_training_in_f10 is False
    assert config.deploy_in_f10 is False
    assert len(canonical_f10_config_sha256(config)) == 64


def test_f10_config_rejects_contract_drift(tmp_path: Path) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["intelligence_retrieval"]["external_fetch_on_request"] = True
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="retrieval boundary drifted"):
        load_backend_integration_config(path)


def test_f10_config_file_is_canonical_json() -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cloned = deepcopy(payload)
    canonical = json.dumps(cloned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    assert hashlib.sha256(canonical.encode()).hexdigest() == canonical_f10_config_sha256(
        load_backend_integration_config(CONFIG_PATH)
    )
