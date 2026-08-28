from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.app.schemas.research import (
    FinancialIntelligenceItem,
    VolatilitySurprisePredictionResponse,
)
from demo.client import DashboardApiClient, DashboardApiError
from demo.contracts import (
    ControlledDashboardFixture,
    DashboardDemoConfig,
    load_controlled_fixture,
    load_dashboard_config,
)
from demo.presentation import (
    band_color,
    band_label,
    event_summary,
    format_percentile,
    format_score,
    sentiment_summary,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "research/configs/dashboard_demo.v1.json"


@st.cache_resource
def load_assets() -> tuple[DashboardDemoConfig, ControlledDashboardFixture]:
    config = load_dashboard_config(CONFIG_PATH)
    fixture = load_controlled_fixture(ROOT / config.fixture_path)
    return config, fixture


def render() -> None:
    st.set_page_config(
        page_title="Financial AI Assistant",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_theme()
    config, fixture = load_assets()

    with st.sidebar:
        st.markdown("### Demo 控制台")
        mode_label = st.radio(
            "資料模式",
            ("受控離線示範", "本機 FastAPI"),
            help="離線模式不會發出任何網路請求。",
        )
        api_base_url = config.local_api_default_base_url
        if mode_label == "本機 FastAPI":
            api_base_url = st.text_input("FastAPI URL", value=api_base_url)
            st.caption("安全限制：僅允許 localhost／127.0.0.1／::1。")
        st.divider()
        st.caption("F11 · controlled public demo")
        st.caption("不含真實持股、LINE token 或個人資料")

    prediction, items, source_label = _resolve_data(
        mode_label, api_base_url, config, fixture
    )
    _render_header(fixture, source_label)
    _render_risk_summary(prediction)

    overview_tab, intelligence_tab, lineage_tab = st.tabs(
        ["風險概覽", "近期情報", "模型與限制"]
    )
    with overview_tab:
        _render_feature_context(fixture)
    with intelligence_tab:
        _render_intelligence(items)
    with lineage_tab:
        _render_lineage(prediction, fixture, source_label)

    st.divider()
    st.caption(
        "本頁僅展示股票相對波動異常研究訊號，不預測漲跌、不是投資建議，"
        "也不保證未來波動。"
    )


def _resolve_data(
    mode_label: str,
    api_base_url: str,
    config: DashboardDemoConfig,
    fixture: ControlledDashboardFixture,
) -> tuple[
    VolatilitySurprisePredictionResponse,
    list[FinancialIntelligenceItem],
    str,
]:
    if mode_label == "受控離線示範":
        return fixture.prediction_response, fixture.intelligence_items, "受控合成離線資料"
    cache_key = f"{api_base_url}|{fixture.prediction_request.ticker}"
    if st.button("重新取得本機資料", width="stretch") or st.session_state.get(
        "live_cache_key"
    ) != cache_key:
        try:
            client = DashboardApiClient(
                api_base_url,
                allowed_hosts=config.allowed_api_hosts,
            )
            st.session_state["live_prediction"] = client.predict(
                fixture.prediction_request
            )
            st.session_state["live_items"] = client.intelligence(
                fixture.prediction_request.ticker,
                limit=config.maximum_intelligence_items,
            ).items
            st.session_state["live_cache_key"] = cache_key
        except (DashboardApiError, ValueError) as error:
            st.error(str(error))
            st.stop()
    return (
        st.session_state["live_prediction"],
        st.session_state["live_items"],
        "本機 F10 FastAPI",
    )


def _render_header(fixture: ControlledDashboardFixture, source_label: str) -> None:
    st.markdown(
        '<div class="eyebrow">FINANCIAL INTELLIGENCE RESEARCH</div>',
        unsafe_allow_html=True,
    )
    st.title("Financial AI Assistant")
    title_col, source_col = st.columns([3, 1])
    with title_col:
        st.subheader(fixture.company_display_name)
    with source_col:
        st.markdown(f"**資料來源模式**  \n{source_label}")
    st.info(fixture.data_notice, icon="🧪")


def _render_risk_summary(prediction: VolatilitySurprisePredictionResponse) -> None:
    band = prediction.risk_band
    score_col, percentile_col, band_col = st.columns(3)
    score_col.metric(
        "Next-session Relative Volatility Surprise",
        format_score(prediction.predicted_volatility_surprise),
        border=True,
        help="相對於個股自身 20-session 歷史波動基準。",
    )
    percentile_col.metric(
        "Historical Risk Percentile",
        format_percentile(prediction.historical_percentile),
        border=True,
        help="相對於 frozen historical OOF reference。",
    )
    band_col.metric(
        "Risk Communication Band",
        f"{band_label(band)} · {band.replace('_', ' ')}",
        border=True,
        help="展示分帶，不是分類器標籤。",
    )
    st.progress(
        int(round(prediction.historical_percentile)),
        text=f"歷史相對位置 · {prediction.historical_percentile:.1f} percentile",
    )
    color = band_color(band)
    st.markdown(
        f'<div class="band-note" style="border-left-color:{color}">'
        "此分數表示相對波動異常程度，不表示上漲或下跌方向。</div>",
        unsafe_allow_html=True,
    )


def _render_feature_context(fixture: ControlledDashboardFixture) -> None:
    st.markdown("### 市場情境摘要")
    st.caption("下列數值為 F11 受控合成 fixture，僅用來示範資訊層次。")
    context = fixture.feature_context
    columns = st.columns(5)
    values = (
        ("20-session 報酬", f"{context.return_20_session_pct:+.1f}%"),
        ("20-session 波動", f"{context.volatility_20_session_pct:.1f}%"),
        ("成交量 Z-score", f"{context.volume_zscore_20:+.1f}σ"),
        ("TAIEX 20-session", f"{context.benchmark_return_20_session_pct:+.1f}%"),
        ("TAIEX Drawdown", f"{context.benchmark_drawdown_20_session_pct:+.1f}%"),
    )
    for column, (label, value) in zip(columns, values, strict=True):
        column.metric(label, value, border=True)
    st.markdown("### 如何閱讀")
    st.markdown(
        "- 模型輸出是下一交易日的**相對波動異常程度**。\n"
        "- Percentile 與 band 來自 frozen historical OOF reference。\n"
        "- 目前證據較支持排序能力，不代表能精準預測實際振幅。"
    )


def _render_intelligence(items: list[FinancialIntelligenceItem]) -> None:
    st.markdown("### 近期金融情報")
    if not items:
        st.info("本機資料庫目前沒有這檔股票的已入庫情報。")
        return
    for item in items:
        with st.container(border=True):
            header_col, time_col = st.columns([3, 1])
            header_col.markdown(f"**{item.source_excerpt or '無摘要'}**")
            time_col.caption(item.published_at.strftime("%Y-%m-%d %H:%M"))
            st.write(sentiment_summary(item))
            st.write(event_summary(item))
            if item.deterministic_cue_terms:
                st.caption("事件線索：" + "、".join(item.deterministic_cue_terms))
            st.caption(f"來源類型：{item.source_type} · 語言：{item.language}")


def _render_lineage(
    prediction: VolatilitySurprisePredictionResponse,
    fixture: ControlledDashboardFixture,
    source_label: str,
) -> None:
    st.markdown("### Model lineage")
    st.code(
        "\n".join(
            (
                f"source_mode={source_label}",
                f"model_version={prediction.model_version}",
                f"feature_pipeline_version={prediction.feature_pipeline_version}",
                f"target_version={prediction.target_version}",
                f"artifact_sha256={prediction.artifact_sha256}",
                f"fixture_id={fixture.fixture_id}",
            )
        ),
        language="text",
    )
    st.markdown("### 已知限制")
    st.markdown(
        "- 本 demo 不代表 prospective validation 或即時投資訊號。\n"
        "- 受控模式不使用真實市場、持股或私人資料。\n"
        "- 中文情緒未通過驗證時必須 abstain。\n"
        "- 事件代理不是人工標注，也不是 sentiment ground truth。\n"
        "- F9 NLP incremental-value study 尚未執行。"
    )


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #f7faf9 0%, #eef4f2 100%); }
        .block-container { max-width: 1240px; padding-top: 2.2rem; }
        .eyebrow { color: #18735f; font-size: .76rem; font-weight: 800;
                   letter-spacing: .16em; margin-bottom: .35rem; }
        h1, h2, h3 { color: #12362f; }
        [data-testid="stMetric"] { background: rgba(255,255,255,.82); }
        .band-note { background: rgba(255,255,255,.74); border-left: 5px solid;
                     border-radius: 8px; margin-top: .8rem; padding: .9rem 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


render()
