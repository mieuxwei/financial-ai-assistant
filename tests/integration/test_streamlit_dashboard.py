from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]


def test_streamlit_dashboard_renders_controlled_offline_mode() -> None:
    app = AppTest.from_file(str(ROOT / "demo/app.py")).run(timeout=20)

    assert not app.exception
    assert app.title[0].value == "Financial AI Assistant"
    assert app.radio[0].value == "首頁"
    assert app.radio[1].value == "受控離線示範"
    assert any("Public Live Web Demo" in success.value for success in app.success)
    assert len(app.metric) >= 4
