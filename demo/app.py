from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.app.schemas.research import FinancialIntelligenceItem
from demo.contracts import (
    ControlledDashboardFixture,
    DashboardDemoConfig,
    PublicWebDemoReleaseConfig,
    load_controlled_fixture,
    load_dashboard_config,
    load_public_release_config,
)
from demo.portfolio import (
    FROZEN_UNIVERSE,
    MAX_DEMO_HOLDINGS,
    BrowserDemoHolding,
    build_holding,
    delete_holding,
    upsert_holding,
)
from demo.presentation import (
    band_label,
    event_summary,
    format_percentile,
    format_score,
    sentiment_summary,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "research/configs/dashboard_demo.v1.json"
PUBLIC_RELEASE_CONFIG_PATH = ROOT / "research/configs/public_web_demo_release.v1.json"
HOLDINGS_STATE_KEY = "web_demo_holdings"
NAVIGATION = ("首頁", "股票分析", "持股健檢", "金融情報", "研究成果", "系統架構", "限制與方法")


@st.cache_resource
def load_assets() -> tuple[DashboardDemoConfig, ControlledDashboardFixture]:
    config = load_dashboard_config(CONFIG_PATH)
    fixture = load_controlled_fixture(ROOT / config.fixture_path)
    return config, fixture


@st.cache_resource
def load_public_release() -> PublicWebDemoReleaseConfig:
    return load_public_release_config(PUBLIC_RELEASE_CONFIG_PATH)


def render(*, public_release: bool = False) -> None:
    st.set_page_config(
        page_title="Financial AI Assistant | Controlled Research Demo",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_theme()
    config, fixture = load_assets()
    release = load_public_release()
    with st.sidebar:
        st.markdown("## Financial AI Assistant")
        st.caption("Public Live Web Demo · 主要作品入口")
        page = st.radio("導覽", NAVIGATION, label_visibility="collapsed")
        st.divider()
        if public_release:
            st.success("Controlled Research Demo")
            st.caption("固定受控資料；零 runtime secret；無外部 provider 呼叫。")
        else:
            mode = st.radio("資料模式", ("受控離線示範", "本機 FastAPI"))
            if mode == "本機 FastAPI":
                st.info("本機開發入口保留；公開版本固定使用受控 fixture。")
        st.divider()
        st.caption("LINE：Experimental Multi-channel Prototype")
        st.caption("非即時市場預測 · 非投資建議")
    pages = {
        "首頁": lambda: _render_landing(fixture, release),
        "股票分析": lambda: _render_stock_analysis(fixture),
        "持股健檢": lambda: _render_portfolio_health(fixture),
        "金融情報": lambda: _render_intelligence_page(fixture.intelligence_items),
        "研究成果": lambda: _render_research_results(release),
        "系統架構": _render_architecture,
        "限制與方法": lambda: _render_limitations(release, fixture),
    }
    pages[page]()
    st.divider()
    st.caption(
        "Controlled Research Demo｜研究的是相對波動異常程度，不預測漲跌；"
        "不構成投資建議或未來結果保證。"
    )


def _go_to(page: str) -> None:
    st.session_state["導覽"] = page


def _render_landing(
    fixture: ControlledDashboardFixture, release: PublicWebDemoReleaseConfig
) -> None:
    st.markdown('<div class="release-badge">CONTROLLED RESEARCH DEMO</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WEB-FIRST PORTFOLIO EXPERIENCE</div>', unsafe_allow_html=True)
    st.title("Financial AI Assistant")
    st.subheader("基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統")
    st.write(
        "結合時間序列機器學習、金融 NLP 與多層應用架構，"
        "提供股票相對波動異常程度與事件情報的研究型分析介面。"
    )
    status, capability, boundary = st.columns(3)
    status.success("Public Live Web Demo\n\n已部署的主要互動入口")
    capability.info("核心能力\n\n風險排序、持股健檢、金融事件情報")
    boundary.warning("研究邊界\n\n非即時推論、不預測漲跌、非投資建議")
    cta_a, cta_b, cta_c = st.columns(3)
    cta_a.button(
        "開始股票分析", type="primary", width="stretch", on_click=_go_to, args=("股票分析",)
    )
    cta_b.button("查看持股健檢", width="stretch", on_click=_go_to, args=("持股健檢",))
    cta_c.button("查看研究方法", width="stretch", on_click=_go_to, args=("研究成果",))
    st.markdown("### 30 秒研究摘要")
    a, b, c, d = st.columns(4)
    a.metric("Final model", "Ridge · α 100", border=True)
    b.metric("Rolling periods", str(release.track_a_outer_folds), border=True)
    c.metric("Mean outer Spearman", f"{release.track_a_mean_outer_spearman:.3f}", border=True)
    d.metric("Top-decile lift", f"{release.track_a_top_decile_lift:.3f}×", border=True)
    st.caption(
        f"受控範例：{fixture.company_display_name}。模型較適合做相對排序，"
        "不代表精準振幅、價格方向或即時市場預測。"
    )


def _render_stock_analysis(fixture: ControlledDashboardFixture) -> None:
    prediction = fixture.prediction_response
    st.markdown('<div class="eyebrow">STOCK ANALYSIS</div>', unsafe_allow_html=True)
    st.title("股票分析")
    st.caption("目前公開版僅以 2330 台積電受控 fixture 展示完整研究訊號。")
    st.subheader(fixture.company_display_name)
    score, percentile, band = st.columns(3)
    score.metric(
        "Relative volatility-surprise score",
        format_score(prediction.predicted_volatility_surprise),
        border=True,
    )
    percentile.metric(
        "Historical percentile",
        format_percentile(prediction.historical_percentile),
        border=True,
    )
    band.metric(
        "Communication band",
        f"{band_label(prediction.risk_band)} · {prediction.risk_band}",
        border=True,
    )
    st.progress(
        int(round(prediction.historical_percentile)), text="相對於 frozen historical OOF reference"
    )
    st.info(
        "這個分數表示下一交易日相對於該股票自身歷史狀態的波動異常程度；它不是機率，也不表示上漲或下跌。"
    )
    st.markdown("### Controlled event intelligence")
    _render_intelligence_cards(fixture.intelligence_items)
    st.warning("目前公開研究版未啟用即時價格與即時模型推論。")


def _render_portfolio_health(fixture: ControlledDashboardFixture) -> None:
    st.markdown('<div class="eyebrow">BROWSER-SESSION SANDBOX</div>', unsafe_allow_html=True)
    st.title("持股健檢")
    st.write(
        "加入 0–5 檔 Demo holdings；資料只存在目前瀏覽器 session，"
        "不需登入，也不會寫入 LINE、Google Sheet 或後端資料庫。"
    )
    st.warning(
        "請勿輸入真實帳戶或其他敏感資訊。此頁沒有即時價格，因此不計算 ROI、市值或未實現損益。"
    )
    holdings = _holdings()
    with st.form("holding-editor", clear_on_submit=False):
        ticker = st.selectbox(
            "股票",
            tuple(FROZEN_UNIVERSE),
            format_func=lambda value: f"{value} {FROZEN_UNIVERSE[value]}",
        )
        shares = st.number_input(
            "股數", min_value=0.01, max_value=10_000_000.0, value=100.0, step=1.0
        )
        average_cost = st.number_input(
            "平均成本（Demo input）", min_value=0.01, max_value=1_000_000.0, value=100.0, step=0.1
        )
        submitted = st.form_submit_button("加入或更新持股", type="primary")
    if submitted:
        try:
            st.session_state[HOLDINGS_STATE_KEY] = upsert_holding(
                holdings, build_holding(ticker, shares, average_cost)
            )
            holdings = _holdings()
            st.success(f"已加入／更新 {ticker}；目前 {len(holdings)}/{MAX_DEMO_HOLDINGS} 檔。")
        except ValueError as error:
            st.error(str(error))
    if not holdings:
        st.info("尚未加入 Demo 持股。請從上方選擇股票、股數與平均成本開始。")
        return
    st.markdown(f"### 我的 Demo holdings（{len(holdings)}/{MAX_DEMO_HOLDINGS}）")
    for holding in holdings:
        with st.container(border=True):
            info, action = st.columns([4, 1])
            info.markdown(f"**{holding['ticker']} {holding['company']}**")
            info.write(f"{holding['shares']:,.2f} 股 · 平均成本 {holding['average_cost']:,.2f}")
            if action.button("刪除", key=f"delete-{holding['ticker']}", width="stretch"):
                st.session_state[HOLDINGS_STATE_KEY] = delete_holding(holdings, holding["ticker"])
                st.rerun()
            if holding["ticker"] == fixture.prediction_request.ticker:
                prediction = fixture.prediction_response
                info.caption(
                    f"受控研究訊號：{format_score(prediction.predicted_volatility_surprise)} · "
                    f"歷史百分位 {format_percentile(prediction.historical_percentile)} · "
                    f"{prediction.risk_band}"
                )
            else:
                info.caption(
                    "此 ticker 尚無 public-safe controlled signal；"
                    "系統安全地顯示 unavailable，不推估或補值。"
                )
    st.markdown("### Portfolio Health")
    st.info("持股健檢整合 browser-session 持股與可用的受控研究訊號；不代表當前市場狀態。")


def _holdings() -> list[BrowserDemoHolding]:
    value = st.session_state.setdefault(HOLDINGS_STATE_KEY, [])
    return [dict(item) for item in value]


def _render_intelligence_page(items: list[FinancialIntelligenceItem]) -> None:
    st.markdown('<div class="eyebrow">FINANCIAL NLP INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("金融情報")
    st.write(
        "系統刻意分離事件分類、市場反應幅度與文字情緒，避免把不同研究概念混成單一 sentiment score。"
    )
    _render_intelligence_cards(items)


def _render_intelligence_cards(items: list[FinancialIntelligenceItem]) -> None:
    if not items:
        st.info("目前沒有可公開的受控金融情報。")
        return
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{item.source_excerpt or '受控事件範例'}**")
            st.caption(f"{item.published_at:%Y-%m-%d %H:%M} · {item.source_type} · {item.language}")
            if item.track_b_intelligence is None:
                st.write(event_summary(item))
                st.write(sentiment_summary(item))
                continue
            track_b = item.track_b_intelligence
            event = track_b.event_classification
            reaction = track_b.market_reaction
            a, b, c = st.columns(3)
            a.markdown(f"**EVENT CLASS**\n\n{event.event_class or '未分類'}")
            b.markdown(
                "**MARKET REACTION MAGNITUDE**\n\n" + (reaction.communication_band or "Unavailable")
            )
            c.markdown("**LINGUISTIC SENTIMENT**\n\n尚未通過獨立驗證")
            st.caption("市場反應強度是歷史幅度關聯的自動化研究訊號，不代表方向、因果或報酬預測。")


def _render_research_results(release: PublicWebDemoReleaseConfig) -> None:
    st.markdown('<div class="eyebrow">RESEARCH EVIDENCE</div>', unsafe_allow_html=True)
    st.title("研究成果")
    st.markdown("### Track A · Stock-normalized volatility surprise")
    a, b, c, d = st.columns(4)
    a.metric("Selected model", "Ridge · α 100", border=True)
    b.metric("Outer periods", str(release.track_a_outer_folds), border=True)
    c.metric("Mean Spearman", f"{release.track_a_mean_outer_spearman:.3f}", border=True)
    d.metric("Top-decile lift", f"{release.track_a_top_decile_lift:.3f}×", border=True)
    st.write(
        "模型的證據主要在跨期相對排序；R² 接近零或略為負值，"
        "因此不宣稱能精準預測振幅，更不預測方向。"
    )
    st.markdown("### Track B · Financial NLP intelligence")
    x, y = st.columns(2)
    x.metric("Metadata magnitude OOF Spearman", "0.250", border=True)
    y.metric("Magnitude top-decile lift", "1.623×", border=True)
    st.markdown(
        "- FSC 金融領域適應完成；BERT-base-Chinese 僅保留為 representation capability。\n"
        "- 中文 linguistic sentiment 未通過獨立驗證，因此 abstain。\n"
        "- BERT text 對 signed market-reaction 的增量價值不受支持，沒有包裝成正面結果。"
    )


def _render_architecture() -> None:
    st.markdown('<div class="eyebrow">SYSTEM ARCHITECTURE</div>', unsafe_allow_html=True)
    st.title("系統架構")
    st.markdown("### Primary Web Experience")
    st.code(
        "Web UI (Streamlit)\n"
        "  ↓\nControlled Research Services + Browser-session Portfolio\n"
        "  ↓\nVersioned Research Artifacts",
        language="text",
    )
    st.markdown("### Experimental Messaging Interface")
    st.code(
        "LINE Demo OA\n  ↓\nCloudflare Security Edge\n  ↓\nGoogle Apps Script\n"
        "  ↓\nFastAPI → PostgreSQL / Neon\n  ↓\nGAS Flex Message → LINE",
        language="text",
    )
    st.info(
        "LINE 版本是多通路整合原型，保留 webhook 驗證、HMAC、GAS 呈現、"
        "FastAPI 串接、使用者隔離與 Sandbox 寫入等工程證據；"
        "主要互動體驗以 Web Demo 為主。"
    )
    st.markdown("### Technology stack")
    st.write(
        "Streamlit · LINE Messaging API / LIFF prototype · Google Apps Script · "
        "Cloudflare Worker · FastAPI · PostgreSQL / Neon · scikit-learn Ridge / "
        "HistGradientBoosting comparison · BERT-base-Chinese domain adaptation · Vercel"
    )


def _render_limitations(
    release: PublicWebDemoReleaseConfig, fixture: ControlledDashboardFixture
) -> None:
    st.markdown('<div class="eyebrow">METHODS & LIMITATIONS</div>', unsafe_allow_html=True)
    st.title("限制與方法")
    st.warning("即時市場推論尚未啟用，因訓練與即時資料的完整特徵一致性尚未通過驗證。")
    a, b = st.columns(2)
    a.metric(
        "F11B-2A gates",
        f"{release.current_market_gate_passed}/{release.current_market_gate_total}",
        border=True,
    )
    b.metric(
        "Exact feature parity",
        f"{release.exact_feature_parity_passed}/{release.exact_feature_parity_total}",
        border=True,
    )
    st.markdown(
        "- Retrospective、leakage-aware、rolling-origin evaluation；不是 prospective validation。\n"
        "- 中文文字情緒目前尚未通過獨立驗證。\n"
        "- Market-reaction magnitude 不是方向預測，也不是因果效果。\n"
        "- Public Demo 無 request-time provider calls、真實持股、個人資料或秘密。"
    )
    st.markdown("### Reproducibility lineage")
    p = fixture.prediction_response
    st.code(
        f"model_version={p.model_version}\nfeature_pipeline_version={p.feature_pipeline_version}\n"
        f"target_version={p.target_version}\nartifact_sha256={p.artifact_sha256}\nfixture_id={fixture.fixture_id}",
        language="text",
    )
    st.markdown("### Future External Validation")
    st.write(
        "未來 TWSE／TPEx forward collection 可形成真正未見資料的 external validation；"
        "排程蒐集不等於自動重訓，也不是目前作品集封案條件。"
    )


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #f7faf9 0%, #eef4f2 100%); }
        .block-container { max-width: 1180px; padding-top: 2rem; }
        .eyebrow {
          color: #18735f; font-size: .76rem; font-weight: 800;
          letter-spacing: .16em; margin-bottom: .35rem;
        }
        .release-badge {
          display: inline-block; background: #12362f; color: white;
          border-radius: 999px; font-size: .78rem; font-weight: 800;
          letter-spacing: .08em; margin-bottom: .75rem; padding: .45rem .8rem;
        }
        h1, h2, h3 { color: #12362f; }
        [data-testid="stMetric"] { background: rgba(255,255,255,.84); }
        @media (max-width: 700px) {
          .block-container { padding: 1rem .8rem 2rem; }
          h1 { font-size: 2rem !important; }
          h2 { font-size: 1.25rem !important; }
          [data-testid="stHorizontalBlock"] { gap: .5rem; }
          button { min-height: 2.75rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render()
