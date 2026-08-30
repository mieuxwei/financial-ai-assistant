import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

from demo.contracts import load_controlled_fixture, load_public_release_config
from demo.portfolio import FROZEN_UNIVERSE

ROOT = Path(__file__).resolve().parents[2]
RELEASE_CONFIG = ROOT / "research/configs/public_web_demo_release.v1.json"
DASHBOARD_FIXTURE = ROOT / "demo/fixtures/controlled_dashboard_demo.v1.json"


def test_public_release_config_is_fixture_only_and_fail_closed() -> None:
    release = load_public_release_config(RELEASE_CONFIG)

    assert release.release_status == "PUBLIC_WEB_DEMO_DEPLOYED"
    assert release.hosting_provider == "STREAMLIT_COMMUNITY_CLOUD"
    assert release.deployment_topology == "STREAMLIT_FIXTURE_ONLY"
    assert release.entrypoint == "demo/public_app.py"
    assert release.python_version == "3.12"
    assert release.controlled_fixture_only is True
    assert release.zero_runtime_secret is True
    assert release.fastapi_required is False
    assert release.request_time_network_calls is False
    assert release.current_market_inference_enabled is False
    assert release.chinese_sentiment_enabled is False
    assert release.price_direction_enabled is False
    assert release.portfolio_input_enabled is True
    assert release.primary_public_experience == "LIVE_WEB_DEMO"
    assert release.line_experience == "EXPERIMENTAL_MULTI_CHANNEL_PROTOTYPE"
    assert release.portfolio_storage == "BROWSER_SESSION_ONLY"
    assert release.line_primary_cta is False
    assert release.private_artifacts_packaged is False


def test_public_fixture_preserves_track_b_abstention_and_reaction_boundary() -> None:
    fixture = load_controlled_fixture(DASHBOARD_FIXTURE)
    chinese = fixture.intelligence_items[0]
    assert chinese.track_b_intelligence is not None

    track_b = chinese.track_b_intelligence
    assert track_b.linguistic_sentiment.polarity is None
    assert track_b.linguistic_sentiment.positive_probability is None
    assert track_b.linguistic_sentiment.neutral_probability is None
    assert track_b.linguistic_sentiment.negative_probability is None
    assert track_b.market_reaction.maturity == "AUTOMATED_SIGNAL_ONLY"
    assert track_b.market_reaction.direction is None
    assert track_b.market_reaction.direction_status == "ABSTAIN_DIRECTION_NOT_SUPPORTED"
    assert track_b.market_reaction.communication_band == "HIGH"
    assert track_b.event_classification.sentiment_ground_truth is False
    assert track_b.event_classification.market_direction is False
    assert track_b.representation.used_for_market_reaction_prediction is False


def test_public_entrypoint_renders_web_first_release_boundaries() -> None:
    app = AppTest.from_file(str(ROOT / "demo/public_app.py"), default_timeout=15).run()

    assert not app.exception
    rendered = "\n".join(
        str(element.value)
        for collection in (
            app.title,
            app.subheader,
            app.markdown,
            app.caption,
            app.info,
            app.warning,
            app.success,
            app.metric,
        )
        for element in collection
    )
    assert "CONTROLLED RESEARCH DEMO" in rendered
    assert "非投資建議" in rendered
    assert "Public Live Web Demo" in rendered
    assert "預測股票相對波動異常程度" in rendered
    assert any(button.label == "開始股票分析" for button in app.button)
    assert not app.sidebar

    app.selectbox[0].set_value("股票分析").run()
    stock_analysis = "\n".join(
        str(element.value)
        for collection in (app.title, app.markdown, app.caption, app.info, app.metric)
        for element in collection
    )
    assert any(metric.label == "相對波動異常分數" for metric in app.metric)
    assert "不是發生機率" in stock_analysis

    app.selectbox[0].set_value("持股健檢").run()
    assert any(button.label == "載入兩檔示範持股" for button in app.button)
    assert any(button.label in {"加入持股", "更新持股"} for button in app.button)

    app.selectbox[0].set_value("金融情報").run()
    intelligence = "\n".join(str(element.value) for element in app.markdown)
    assert "歷史市場反應幅度" in intelligence
    assert "中文文字情緒" in intelligence
    assert "尚未通過獨立驗證" in intelligence

    app.selectbox[0].set_value("限制與方法").run()
    limitations = "\n".join(
        str(element.value)
        for collection in (app.markdown, app.warning, app.metric)
        for element in collection
    )
    assert "即時市場推論尚未啟用" in limitations
    assert any(expander.label == "為什麼尚未啟用即時推論？" for expander in app.expander)
    assert not any("gate" in metric.label.casefold() for metric in app.metric)
    assert not any("parity" in metric.label.casefold() for metric in app.metric)
    assert "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED" not in limitations


def test_public_release_packaging_has_no_secret_or_private_dependency() -> None:
    entrypoint = (ROOT / "demo/public_app.py").read_text(encoding="utf-8")
    requirements = (ROOT / "demo/requirements.txt").read_text(encoding="utf-8")
    release_config = RELEASE_CONFIG.read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "render(public_release=True)" in entrypoint
    assert "http" not in entrypoint.casefold()
    assert ".env" not in release_config
    assert ".tools/private" not in release_config
    assert "fastapi" not in requirements.casefold()
    assert "httpx" not in requirements.casefold()
    assert ".tools/" in gitignore
    assert ".streamlit/secrets.toml" in gitignore

    app_source = (ROOT / "demo/app.py").read_text(encoding="utf-8")
    assert "@media (max-width: 700px)" in app_source
    assert "requests." not in app_source
    assert "httpx." not in app_source


def test_public_demo_ticker_selection_fails_closed_without_borrowing_signal() -> None:
    for ticker in FROZEN_UNIVERSE:
        app = AppTest.from_file(str(ROOT / "demo/public_app.py"), default_timeout=15).run()
        app.selectbox[0].set_value("股票分析").run()
        app.selectbox[1].set_value(ticker).run()

        has_score = any(metric.label == "相對波動異常分數" for metric in app.metric)
        rendered = "\n".join(str(element.value) for element in app.info)
        if ticker == "2330":
            assert has_score
            assert "不補值" not in rendered
        else:
            assert not has_score
            assert "不補值" in rendered
            assert "不製造即時預測" in rendered


def test_public_demo_sample_portfolio_exposes_supported_and_unavailable_states() -> None:
    app = AppTest.from_file(str(ROOT / "demo/public_app.py"), default_timeout=15).run()
    app.selectbox[0].set_value("持股健檢").run()
    sample = next(button for button in app.button if button.label == "載入兩檔示範持股")
    sample.click().run()

    rendered = "\n".join(
        str(element.value)
        for collection in (app.markdown, app.caption, app.info, app.metric)
        for element in collection
    )
    assert "2330 台積電" in rendered
    assert "0050 元大台灣50" in rendered
    assert "相對波動異常 0.80×" in rendered
    assert "不推估、不補值" in rendered
    assert any(metric.label == "Demo 持股" and metric.value == "2/5" for metric in app.metric)


def test_nested_entrypoint_resolves_project_package_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "demo/public_app.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0
    assert "ModuleNotFoundError" not in result.stderr
