import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/f11b_line_integration_design.v1.json"
DOC = ROOT / "docs/f11b_line_product_design_freeze.md"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_main_menu_is_exactly_the_six_frozen_product_entries() -> None:
    config = _config()
    assert [item["id"] for item in config["main_menu"]] == [
        "stock_analysis",
        "portfolio_check",
        "financial_intelligence",
        "import_holdings",
        "news_research",
        "settings",
    ]
    menu_ids = {item["id"] for item in config["main_menu"]}
    assert menu_ids.isdisjoint(config["forbidden_main_menu_capabilities"])
    assert "morning_report" not in menu_ids
    assert "closing_report" not in menu_ids
    assert "chinese_sentiment" not in menu_ids
    assert "direction_prediction" not in menu_ids


def test_preferences_roles_and_admin_visibility_are_user_scoped() -> None:
    config = _config()
    assert config["settings"]["preference_scope"] == "PER_USER"
    assert config["settings"]["notifications"] == [
        "morning_report_enabled",
        "closing_report_enabled",
    ]
    assert "provider_quota_admin" not in config["roles"]["REGISTERED"]
    assert "provider_quota_admin" in config["roles"]["ADMIN"]
    assert config["user_isolation"]["isolation_key"] == "INTERNAL_USER_UUID"
    assert config["user_isolation"]["global_portfolio_allowed"] is False
    assert config["user_isolation"]["global_notification_switch_allowed"] is False


def test_authentication_and_gas_backend_ownership_are_fail_closed() -> None:
    config = _config()
    assert config["identity"]["line_user_id_is_public_backend_token"] is False
    assert config["identity"]["x_user_id_contract"].startswith("DEVELOPMENT_ONLY")
    assert config["identity"]["production_webhook_gate"] == (
        "TERMINATE_AT_RAW_BODY_AND_HEADER_CAPABLE_VERIFICATION_EDGE"
    )
    assert (
        config["gas_to_backend_auth"][
            "gas_asserted_line_user_id_trusted_without_verified_origin"
        ]
        is False
    )
    gas = set(config["ownership"]["gas"])
    fastapi = set(config["ownership"]["fastapi"])
    forbidden = set(config["ownership"]["forbidden_in_gas"])
    assert "track_a_inference" in fastapi
    assert "portfolio_business_rules" in fastapi
    assert "portfolio_business_logic" in forbidden
    assert gas.isdisjoint(forbidden)


def test_current_market_gate_and_non_mutation_boundary_cannot_be_bypassed() -> None:
    config = _config()
    assert len(config["f11b_2_gate"]) == 9
    assert config["f11b_2_gate_bypass_allowed"] is False
    assert config["controlled_demo"]["portfolio_write_allowed"] is False
    assert config["live_gas_modified"] is False
    assert config["deployed"] is False
    assert config["portfolio_mutated"] is False
    assert config["track_a_modified"] is False
    assert config["track_b_models_modified"] is False
    assert config["next_executable_unit"] == (
        "F11B-1A_CONTROLLED_LINE_ROUTING_IN_MIGRATION_COPY"
    )


def test_design_document_contains_required_matrices_and_risks() -> None:
    document = DOC.read_text(encoding="utf-8")
    for required in (
        "Legacy feature preservation matrix",
        "User data isolation matrix",
        "LINE signature is currently unverified",
        "clear-and-rebuild",
        "F11B-1A routing freeze",
        "F11B-1B controlled demo",
        "F11B-2 current-market gate",
        "F11B-1A — Controlled LINE Routing in Migration Copy",
    ):
        assert required in document
