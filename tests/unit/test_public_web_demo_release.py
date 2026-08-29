import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

import demo.app as dashboard_app
from demo.contracts import load_controlled_fixture, load_public_release_config

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
    assert release.portfolio_input_enabled is False
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


def test_public_entrypoint_bypasses_api_and_renders_release_boundaries(monkeypatch) -> None:
    def reject_api_path(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("public fixture mode attempted to resolve API data")

    monkeypatch.setattr(dashboard_app, "_resolve_data", reject_api_path)
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
    assert "不是投資建議" in rendered
    assert "不表示上漲或下跌方向" in rendered
    assert "市場反應強度" in rendered
    assert "中文情緒：不輸出（尚未通過驗證）" in rendered
    assert "即時市場推論尚未啟用" in rendered
    assert "6/9" in rendered
    assert "5/23" in rendered
    assert "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED" not in rendered


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
