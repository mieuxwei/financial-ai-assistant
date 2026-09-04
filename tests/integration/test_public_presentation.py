"""Presentation-only regression: historical evidence, navigation and session holdings."""

from pathlib import Path

import httpx
import requests
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]


def _app() -> AppTest:
    return AppTest.from_file(str(ROOT / "demo/public_app.py"), default_timeout=30).run()


def _button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def test_cross_page_ticker_context_and_no_event_substitution() -> None:
    app = _app()
    _button(app, "開始股票分析").click().run()
    for ticker in ("2308", "0050"):
        app.selectbox[1].set_value(ticker).run()
        _button(app, "金融情報").click().run()
        assert app.selectbox[1].value == ticker
        if ticker == "0050":
            assert any("不補寫事件" in item.value for item in app.info)
            assert not any("類重大訊息" in item.value for item in app.markdown)
        else:
            assert any("2308 台達電" in item.value for item in app.markdown)
        _button(app, "股票分析").click().run()
        assert app.selectbox[1].value == ticker
        assert not app.exception


def test_portfolio_ui_create_update_limit_delete_and_session_isolation() -> None:
    app = _app()
    app.selectbox[0].set_value("持股健檢").run()
    _button(app, "載入三檔完整示範持股").click().run()
    assert len(app.session_state["web_demo_holdings"]) == 3
    app.selectbox[1].set_value("2330").run()
    app.number_input[0].set_value(123.0)
    _button(app, "更新持股").click().run()
    assert app.session_state["web_demo_holdings"][0]["shares"] == 123
    for ticker in ("1303", "2317", "2412"):
        app.selectbox[1].set_value(ticker).run()
        _button(app, "加入持股").click().run()
    assert len(app.session_state["web_demo_holdings"]) == 5
    assert any("最多只能加入 5 檔" in item.value for item in app.error)
    app.button(key="delete-1303").click().run()
    assert len(app.session_state["web_demo_holdings"]) == 4
    independent = _app()
    independent.selectbox[0].set_value("持股健檢").run()
    assert independent.session_state["web_demo_holdings"] == []
    _button(app, "清空 Demo 持股").click().run()
    assert app.session_state["web_demo_holdings"] == []
    assert not app.exception


def test_public_pages_render_without_outbound_http(monkeypatch) -> None:
    def reject(*args, **kwargs):
        raise AssertionError("Public presentation must not make outbound HTTP calls")

    monkeypatch.setattr(requests.sessions.Session, "request", reject)
    monkeypatch.setattr(httpx.Client, "request", reject)
    app = _app()
    for page in ("股票分析", "金融情報", "研究成果", "系統架構", "限制與方法", "研究與系統說明"):
        app.selectbox[0].set_value(page).run()
        assert not app.exception
        assert not app.error


def test_public_copy_and_evidence_links() -> None:
    readme = (ROOT / "README.md").read_text()
    overview = (ROOT / "docs/project_overview_status_and_technology.md").read_text()
    app = (ROOT / "demo/app.py").read_text()
    assert "Independent ML & Financial NLP Research Project" in readme
    assert "project_overview_status_and_technology.md" in readme
    assert "[README](../README.md)" in overview
    for value in (
        "20,637",
        "0.1940",
        "0.5473",
        "1.3542",
        "7,582",
        "3,433",
        "0.2504",
        "1.623",
        "5/23",
        "6/9",
    ):
        assert value in readme
    for term in ("教授", "面試官", "招生委員", "履歷"):
        assert term not in readme + overview + app
    assert 'link_button("查看 GitHub"' in app
    assert "不是發生機率" in app
    assert "中文文字情緒尚未通過獨立驗證" in app
