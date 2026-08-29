import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/r1b_line_public_beta.v1.json"


def test_r1b_release_config_freezes_safe_manual_setup_state() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["release_status"] == "LINE_PUBLIC_BETA_READY_FOR_MANUAL_SETUP"
    assert config["deployment_status"] == "NOT_DEPLOYED"
    assert config["private_environment_unchanged"] is True
    assert config["architecture"]["security_edge"] == "CLOUDFLARE_WORKER"
    assert config["architecture"]["request_time_providers"] == []
    assert config["identity"]["raw_line_user_id_persisted"] is False
    assert config["security"]["line_signature_raw_body_required"] is True
    assert config["portfolio"]["max_holdings_per_principal"] == 5
    assert config["portfolio"]["retention_days"] == 30
    assert config["portfolio"]["current_price_enabled"] is False
    assert config["portfolio"]["roi_enabled"] is False
    assert config["research_boundary"]["current_market_f7_enabled"] is False
    assert config["research_boundary"]["current_feature_parity"] == "5/23"
    assert config["research_boundary"]["current_market_gates"] == "6/9"
    assert config["research_boundary"]["chinese_sentiment_enabled"] is False
    assert config["external_setup"]["line_demo_qr"] == "LINE_DEMO_QR_PENDING"


def test_r1b_documents_preserve_private_public_separation_and_rollback() -> None:
    architecture = (ROOT / "docs/line_public_beta_architecture.md").read_text(encoding="utf-8")
    setup = (ROOT / "docs/line_public_beta_setup.md").read_text(encoding="utf-8")
    result = (ROOT / "research/evaluation/r1b_line_public_beta_result.md").read_text(
        encoding="utf-8"
    )
    for content in (architecture, setup, result):
        assert "LINE_PUBLIC_BETA_READY_FOR_MANUAL_SETUP" in content
        assert "private" in content.casefold()
    assert "Cloudflare Worker" in architecture
    assert "raw LINE user ID" in architecture
    assert "Disable the Demo LINE webhook" in setup
    assert "Do not provide tokens" in setup
    assert "LINE_DEMO_QR_PENDING" in result
