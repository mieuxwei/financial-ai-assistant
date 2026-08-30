from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIFF_ROOT = ROOT / "backend" / "app" / "static" / "demo_liff"


def test_liff_client_uses_verified_token_exchange_without_profile_identity() -> None:
    script = (LIFF_ROOT / "app.js").read_text(encoding="utf-8")
    assert "liff.getIDToken()" in script
    assert "/api/v1/demo/liff/session" in script
    assert "getDecodedIDToken" not in script
    assert "getProfile" not in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_liff_editor_requires_preview_and_one_batch_confirmation() -> None:
    html = (LIFF_ROOT / "index.html").read_text(encoding="utf-8")
    script = (LIFF_ROOT / "app.js").read_text(encoding="utf-8")
    assert "預覽並確認" in html
    assert "確認儲存" in html
    assert 'method: "PUT"' in script
    assert "/api/v1/demo/liff/portfolio" in script
    assert "expected_portfolio_version" in script
    assert "最多 5 檔" in html


def test_liff_editor_preserves_research_and_privacy_boundaries() -> None:
    combined = "\n".join(
        (LIFF_ROOT / name).read_text(encoding="utf-8")
        for name in ("index.html", "app.js")
    )
    assert "不取得即時價格" in combined
    assert "不預測股價上漲或下跌" in combined
    assert "最長 30 天" in combined
    assert "Positive" not in combined and "Negative" not in combined
    assert "買進" not in combined and "賣出" not in combined
