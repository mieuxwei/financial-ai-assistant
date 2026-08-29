from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAS_ROOT = ROOT / "line_adapter/public_beta"


def _all_demo_gas() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(GAS_ROOT.glob("*.gs")))


def test_public_demo_gas_is_separate_and_contains_no_secret_or_private_resource() -> None:
    source = _all_demo_gas()
    assert GAS_ROOT.is_dir()
    assert "DEMO_EDGE_GAS_SHARED_SECRET" in source
    assert "DEMO_GAS_SERVICE_TOKEN" in source
    assert "LINE_DEMO_CHANNEL_ACCESS_TOKEN" in source
    assert "PropertiesService.getScriptProperties" in source
    assert "LINE_DEMO_CHANNEL_ACCESS_TOKEN =" not in source
    assert "SpreadsheetApp.openById" not in source
    assert "script.google.com/macros/s/" not in source
    assert "LINE_USER_ID" not in source
    assert "Gemini" not in source
    assert "Perplexity" not in source


def test_public_beta_requires_preview_confirmation_before_writes() -> None:
    source = _all_demo_gas()
    assert 'state.step = "ADD_CONFIRM"' in source
    assert 'state.step = "UPDATE_CONFIRM"' in source
    assert 'step: "DELETE_CONFIRM"' in source
    assert 'requireState_(state, "ADD_CONFIRM")' in source
    assert 'requireState_(state, "UPDATE_CONFIRM")' in source
    assert 'requireState_(state, "DELETE_CONFIRM")' in source
    assert "Idempotency-Key" in source
    assert "enforceDemoRateLimit_" in source
    assert "DEMO_USER_COMMANDS_PER_MINUTE_ = 30" in source


def test_claim_safety_and_privacy_disclosure_are_present() -> None:
    source = _all_demo_gas()
    assert "Controlled Research Demo" in source
    assert "不預測股價上漲或下跌" in source
    assert "中文文字情緒目前尚未通過獨立驗證" in source
    assert "請勿輸入帳號、身分資料或其他敏感資訊" in source
    assert "最長保存 30 天" in source
    assert "即時市場推論尚未啟用" in source


def test_public_beta_does_not_contain_unsupported_product_claims() -> None:
    source = _all_demo_gas().casefold()
    for forbidden in (
        "target price",
        "reliable up/down",
        "positive_probability",
        "negative_probability",
        "current-market f7",
    ):
        assert forbidden not in source
