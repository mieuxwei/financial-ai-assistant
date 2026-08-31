import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/f12_portfolio_finalization.v1.json"
RELEASE_CONFIG_PATH = ROOT / "research/configs/portfolio_release.v1.json"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_f12_is_documentation_only_and_preserves_frozen_boundaries() -> None:
    config = _config()

    assert config["milestone"] == "F12"
    assert config["status"] == "COMPLETE"
    assert config["portfolio_only"] is True
    assert config["research_state"]["track_a"] == "COMPLETE_FROZEN"
    assert config["research_state"]["current_market"] == "NOT_READY_FOR_F11B_2"
    assert config["research_state"]["current_market_gate_passed"] == 6
    assert config["research_state"]["current_market_gate_total"] == 9
    assert config["research_state"]["exact_feature_parity_passed"] == 5
    assert config["research_state"]["exact_feature_parity_total"] == 23
    assert config["validation"] == {
        "pytest_passed": 306,
        "ruff": "PASS",
        "secret_scan": "PASS",
        "git_diff_check": "PASS",
    }
    assert all(value is False for value in config["non_goals"].values())


def test_f12_claim_boundaries_are_fail_closed() -> None:
    claims = _config()["claim_boundaries"]

    assert claims["prospective_validation"] is False
    assert claims["live_current_market_inference"] is False
    assert claims["price_direction_supported"] is False
    assert claims["investment_advice"] is False
    assert claims["chinese_sentiment_validated"] is False
    assert claims["market_reaction_causal"] is False
    assert claims["controlled_demo_label_required"] is True


def test_f12_assets_and_documents_exist() -> None:
    config = _config()

    for relative_path in config["assets"] + config["documents"]:
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert path.stat().st_size > 0, relative_path


def test_portfolio_copy_preserves_supported_and_abstained_capabilities() -> None:
    combined = "\n".join((_read("README.md"), _read("docs/portfolio_finalization.md")))

    assert "AUTOMATED_SIGNAL_ONLY" in combined
    assert "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED" in combined
    assert "ABSTAIN_DIRECTION_NOT_SUPPORTED" in combined
    assert "OFFICIAL_OHLCV_AVAILABLE_BUT_ADJUSTED_PARITY_UNRESOLVED" in combined
    assert "NOT_READY_FOR_F11B_2" in combined
    assert "5/23" in combined
    assert "6/9" in combined
    assert "not current-market inference" in combined.casefold()
    assert "not deployed" in combined


def test_generated_svg_assets_include_frozen_evidence_labels() -> None:
    architecture = _read("docs/assets/system_architecture.svg")
    comparison = _read("docs/assets/track_a_model_comparison.svg")
    deciles = _read("docs/assets/track_a_ridge_deciles.svg")

    assert "Current-market serving: BLOCKED" in architecture
    assert "F11B-2A exact feature parity 5/23" in architecture
    assert "Ridge" in comparison and "HGB" in comparison and "Persistence" in comparison
    assert "0.1940" in comparison
    assert "D1" in deciles and "D10" in deciles
    assert "9/9" in deciles


def test_portfolio_markdown_local_links_resolve() -> None:
    for relative_path in ("README.md", "docs/portfolio_finalization.md"):
        document = ROOT / relative_path
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (document.parent / target.split("#", 1)[0]).resolve()
            assert resolved.exists(), f"{relative_path}: {target}"


def test_v1_portfolio_release_freezes_claim_and_serving_boundaries() -> None:
    config = json.loads(RELEASE_CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["release_version"] == "1.0.0"
    assert config["state"] == "V1_0_PORTFOLIO_FROZEN"
    assert config["track_a"]["model"] == "ridge_regression"
    assert config["track_a"]["alpha"] == 100
    assert config["track_b"]["chinese_linguistic_sentiment"].startswith("ABSTAIN")
    assert config["current_market_inference"]["enabled"] is False
    assert config["forward_collection"]["automatic_retraining"] is False
    assert config["line"]["primary_experience"] is False
    assert all(value is False for value in config["research_claims"].values())
    assert config["next_action"] == "NONE_V1_0_PORTFOLIO_COMPLETE"
