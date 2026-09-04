from __future__ import annotations

from pathlib import Path

import streamlit as st

from demo.contracts import (
    ControlledDashboardFixture,
    DashboardDemoConfig,
    HistoricalEvidenceFixture,
    PublicWebDemoReleaseConfig,
    TickerEvidence,
    load_controlled_fixture,
    load_dashboard_config,
    load_historical_evidence_fixture,
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
from demo.presentation import band_label, format_percentile, format_score

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/mieuxwei/financial-ai-assistant"
EVIDENCE_BASE_URL = f"{REPOSITORY_URL}/blob/v1.0.0-portfolio"
CONFIG_PATH = ROOT / "research/configs/dashboard_demo.v1.json"
PUBLIC_RELEASE_CONFIG_PATH = ROOT / "research/configs/public_web_demo_release.v1.json"
HISTORICAL_EVIDENCE_PATH = ROOT / "demo/fixtures/controlled_historical_evidence.v1.json"
HOLDINGS_STATE_KEY = "web_demo_holdings"
SELECTED_TICKER_STATE_KEY = "web_demo_selected_ticker"
NAVIGATION = (
    "首頁",
    "股票分析",
    "持股健檢",
    "金融情報",
    "研究成果",
    "系統架構",
    "限制與方法",
    "研究與系統說明",
)
NAVIGATION_LABELS = {
    "首頁": "首頁｜專題導覽",
    "股票分析": "股票分析｜受控研究訊號",
    "持股健檢": "持股健檢｜Demo Sandbox",
    "金融情報": "金融情報｜事件與 NLP",
    "研究成果": "研究成果｜模型與證據",
    "系統架構": "系統架構｜工程實作",
    "限制與方法": "限制與方法｜研究邊界",
    "研究與系統說明": "研究與系統說明｜Technical Notes",
}


@st.cache_resource
def load_assets() -> tuple[
    DashboardDemoConfig, ControlledDashboardFixture, HistoricalEvidenceFixture
]:
    config = load_dashboard_config(CONFIG_PATH)
    fixture = load_controlled_fixture(ROOT / config.fixture_path)
    evidence = load_historical_evidence_fixture(HISTORICAL_EVIDENCE_PATH)
    return config, fixture, evidence


@st.cache_resource
def load_public_release() -> PublicWebDemoReleaseConfig:
    return load_public_release_config(PUBLIC_RELEASE_CONFIG_PATH)


def render(*, public_release: bool = False) -> None:
    st.set_page_config(
        page_title="Financial AI Assistant | Controlled Research Demo",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_theme()
    try:
        with st.spinner("載入受控研究資料…"):
            config, fixture, evidence = load_assets()
            release = load_public_release()
    except Exception:
        if not public_release:
            raise
        st.error("目前無法載入受控研究資料，請稍後重新整理頁面。")
        st.caption("系統已隱藏內部錯誤細節，且不會改用未驗證或即時來源補值。")
        if st.button("重新載入"):
            st.cache_resource.clear()
            st.rerun()
        return
    if not public_release:
        with st.sidebar:
            st.markdown("## Financial AI Assistant")
            st.caption("本機研究介面")
            mode = st.radio("資料模式", ("受控離線示範", "本機 FastAPI"))
            if mode == "本機 FastAPI":
                st.info("本機開發入口保留；公開版本固定使用受控 fixture。")
            st.divider()
            st.caption("LINE：實驗性多通路整合原型")
            st.caption("非即時市場預測 · 非投資建議")
    page = st.selectbox(
        "頁面導覽",
        NAVIGATION,
        key="navigation",
        format_func=lambda value: NAVIGATION_LABELS[value],
    )
    pages = {
        "首頁": lambda: _render_landing(fixture, release),
        "股票分析": lambda: _render_stock_analysis(evidence),
        "持股健檢": lambda: _render_portfolio_health(evidence),
        "金融情報": lambda: _render_intelligence_page(evidence),
        "研究成果": lambda: _render_research_results(release),
        "系統架構": _render_architecture,
        "限制與方法": lambda: _render_limitations(release, fixture),
        "研究與系統說明": lambda: _render_technical_notes(release, evidence),
    }
    pages[page]()
    st.divider()
    st.caption(
        "Controlled Research Demo｜研究的是相對波動異常程度，不預測漲跌；"
        "不構成投資建議或未來結果保證。"
    )


def _go_to(page: str) -> None:
    st.session_state["navigation"] = page


def _select_ticker(ticker: str) -> None:
    st.session_state[SELECTED_TICKER_STATE_KEY] = ticker


def _open_ticker_page(page: str, ticker: str) -> None:
    _go_to(page)
    _select_ticker(ticker)
    st.session_state["intelligence_ticker"] = ticker


def _render_related_pages(ticker: str, *, key: str) -> None:
    st.markdown("#### 繼續探索")
    stock, intelligence, portfolio = st.columns(3)
    stock.button(
        "股票分析",
        key=f"{key}-stock",
        width="stretch",
        on_click=_open_ticker_page,
        args=("股票分析", ticker),
    )
    intelligence.button(
        "金融情報",
        key=f"{key}-intelligence",
        width="stretch",
        on_click=_open_ticker_page,
        args=("金融情報", ticker),
    )
    portfolio.button(
        "Demo 持股",
        key=f"{key}-portfolio",
        width="stretch",
        on_click=_go_to,
        args=("持股健檢",),
    )
    st.button("查看研究證據", key=f"{key}-research", on_click=_go_to, args=("研究成果",))


def _render_landing(
    fixture: ControlledDashboardFixture, release: PublicWebDemoReleaseConfig
) -> None:
    st.markdown('<div class="release-badge">CONTROLLED RESEARCH DEMO</div>', unsafe_allow_html=True)
    st.title("Financial AI Assistant")
    st.caption("Independent ML & Financial NLP Research Project · v1.0.0-portfolio")
    st.subheader("預測股票相對波動異常程度，整合金融事件情報")
    st.write(
        "研究下一交易日相對於個股自身歷史水準的波動異常程度，"
        "並將金融事件類型與歷史市場反應幅度分開呈現。"
    )
    st.info(
        "v1.0 研究已完成並凍結。這裡展示受控歷史 OOF 快照與允許公開的衍生事件 metadata，"
        "不是合成市場資料、即時行情或現場模型推論；不預測漲跌，非投資建議。"
    )
    cta_a, cta_b = st.columns(2)
    cta_a.button(
        "開始股票分析", type="primary", width="stretch", on_click=_go_to, args=("股票分析",)
    )
    cta_b.link_button("查看 GitHub", REPOSITORY_URL, width="stretch")
    with st.expander("其他入口與資料說明"):
        st.button("查看持股健檢", on_click=_go_to, args=("持股健檢",))
        st.button("查看研究方法", on_click=_go_to, args=("研究成果",))
        st.write(
            "10 檔股票均有歷史研究分數，其中 9 檔有可公開事件；0050 不補造事件。"
            "Demo 持股是暫存輸入，歷史分數與事件不是合成新聞或行情。"
        )
    st.markdown("### Historical evidence｜歷史研究證據")
    a, b, c = st.columns(3)
    a.metric("跨期測試", f"{release.track_a_outer_folds} 段", border=True)
    b.metric("平均排序相關", f"{release.track_a_mean_outer_spearman:.4f}", border=True)
    c.metric("Top-decile lift", "1.3542×", border=True)
    st.caption(
        "Track A：10 檔股票、20,637 筆 historical OOS rows、7 個 rolling-origin outer periods。"
        "結果是有限的歷史排序訊號；"
        "完整模型比較、R² 限制與方法可在「研究成果」查看。"
    )


def _render_stock_analysis(evidence: HistoricalEvidenceFixture) -> None:
    by_ticker = {item.ticker: item for item in evidence.tickers}
    default_ticker = "2330"
    selected_ticker = st.selectbox(
        "選擇受控歷史研究股票",
        tuple(FROZEN_UNIVERSE),
        index=tuple(FROZEN_UNIVERSE).index(
            st.session_state.get(SELECTED_TICKER_STATE_KEY, default_ticker)
        ),
        format_func=lambda value: (
            f"{'✓' if by_ticker[value].coverage == 'FULL_DEMO_READY' else '○'} "
            f"{value} {FROZEN_UNIVERSE[value]}"
        ),
        key=SELECTED_TICKER_STATE_KEY,
    )
    item = by_ticker[selected_ticker]
    prediction = item.track_a
    st.markdown('<div class="eyebrow">STOCK ANALYSIS</div>', unsafe_allow_html=True)
    st.title("股票分析")
    st.caption("✓ 代表分數與事件皆可展示；○ 代表有分數，但目前沒有可公開事件。")
    st.subheader(f"{selected_ticker} {FROZEN_UNIVERSE[selected_ticker]}")
    if prediction is None:
        st.info("此股票目前沒有可公開的受控研究訊號。")
        return
    st.caption(
        f"受控歷史研究快照｜特徵日 {prediction.feature_session}｜"
        "來自已凍結的歷史外推結果；不是今日或即時預測。"
    )
    score, percentile, band = st.columns(3)
    score.metric(
        "相對波動異常分數",
        format_score(str(prediction.score)),
        border=True,
    )
    percentile.metric(
        "歷史相對位置",
        format_percentile(prediction.historical_percentile),
        border=True,
    )
    band.metric(
        "溝通分級",
        band_label(prediction.band),
        border=True,
    )
    st.progress(
        int(round(prediction.historical_percentile)),
        text=f"高於約 {prediction.historical_percentile:.1f}% 的歷史研究樣本",
    )
    st.info(
        "如何閱讀：分數衡量下一交易日的波動幅度，相對於這檔股票近期自身波動水準有多異常。"
        "百分位是分數在歷史研究樣本中的相對位置，不是發生機率；"
        "分級是依既定歷史分數邊界轉成的溝通標籤，不是另一個模型，也不表示上漲或下跌。"
    )
    st.markdown("### 受控事件情報")
    _render_event_card(item)
    st.caption("股票分數與事件案例分屬兩條獨立研究線；日期不一定相同，不構成事件當日的聯合預測。")
    _render_related_pages(selected_ticker, key="stock-related")


def _render_portfolio_health(evidence: HistoricalEvidenceFixture) -> None:
    by_ticker = {item.ticker: item for item in evidence.tickers}
    st.markdown('<div class="eyebrow">BROWSER-SESSION SANDBOX</div>', unsafe_allow_html=True)
    st.title("持股健檢")
    st.write(
        "加入 0–5 檔 Demo 持股；資料只存在目前瀏覽器 session，"
        "不需登入，也不會寫入 LINE、Google Sheet 或後端資料庫。"
    )
    st.caption("請勿輸入敏感資訊。本頁沒有即時價格，因此不計算 ROI、市值或未實現損益。")
    holdings = _holdings()
    sample, reset = st.columns(2)
    st.caption(
        "建議先載入範例：2330、2308、1301。股數與成本僅為 Demo 輸入；載入會取代本次 session 持股。"
    )
    if sample.button("載入三檔完整示範持股", width="stretch", type="primary"):
        st.session_state[HOLDINGS_STATE_KEY] = [
            build_holding("2330", 100, 800),
            build_holding("2308", 40, 420),
            build_holding("1301", 200, 55),
        ]
        holdings = _holdings()
    if reset.button("清空 Demo 持股", width="stretch", disabled=not holdings):
        st.session_state[HOLDINGS_STATE_KEY] = []
        st.rerun()
    selected_ticker = st.selectbox(
        "股票",
        tuple(FROZEN_UNIVERSE),
        format_func=lambda value: f"{value} {FROZEN_UNIVERSE[value]}",
    )
    existing = next((item for item in holdings if item["ticker"] == selected_ticker), None)
    with st.form("holding-editor", clear_on_submit=False):
        shares = st.number_input(
            "股數",
            min_value=0.01,
            max_value=10_000_000.0,
            value=float(existing["shares"] if existing else 100.0),
            step=1.0,
            key=f"shares-{selected_ticker}",
        )
        average_cost = st.number_input(
            "平均成本（僅作 Demo 輸入）",
            min_value=0.01,
            max_value=1_000_000.0,
            value=float(existing["average_cost"] if existing else 100.0),
            step=0.1,
            key=f"cost-{selected_ticker}",
        )
        submitted = st.form_submit_button("更新持股" if existing else "加入持股", type="primary")
    if submitted:
        try:
            st.session_state[HOLDINGS_STATE_KEY] = upsert_holding(
                holdings, build_holding(selected_ticker, shares, average_cost)
            )
            holdings = _holdings()
            st.success(
                f"已{'更新' if existing else '加入'} {selected_ticker}；"
                f"目前 {len(holdings)}/{MAX_DEMO_HOLDINGS} 檔。"
            )
        except ValueError as error:
            st.error(str(error))
    if not holdings:
        st.info("尚未加入 Demo 持股。可載入範例，或從上方選擇股票、股數與平均成本開始。")
        return
    st.markdown("### 健檢摘要")
    available = sum(by_ticker[item["ticker"]].track_a is not None for item in holdings)
    total_col, signal_col, unavailable_col = st.columns(3)
    total_col.metric("Demo 持股", f"{len(holdings)}/{MAX_DEMO_HOLDINGS}", border=True)
    signal_col.metric("有受控研究訊號", available, border=True)
    unavailable_col.metric("安全地不輸出", len(holdings) - available, border=True)
    st.markdown("### 我的 Demo 持股")
    for holding in holdings:
        with st.container(border=True):
            info, action = st.columns([3, 1])
            info.markdown(f"**{holding['ticker']} {holding['company']}**")
            info.write(f"{holding['shares']:,.2f} 股 · 平均成本 {holding['average_cost']:,.2f}")
            if action.button("刪除", key=f"delete-{holding['ticker']}", width="stretch"):
                st.session_state[HOLDINGS_STATE_KEY] = delete_holding(holdings, holding["ticker"])
                st.rerun()
            evidence_item = by_ticker[holding["ticker"]]
            if evidence_item.track_a is not None:
                prediction = evidence_item.track_a
                score_text = format_score(str(prediction.score))
                info.caption(
                    f"受控研究訊號：相對波動異常 {score_text} · "
                    f"歷史百分位 {format_percentile(prediction.historical_percentile)} · "
                    f"{band_label(prediction.band)}"
                )
                if evidence_item.event is not None:
                    event = evidence_item.event
                    info.write(
                        f"事件摘要：{event.summary} 歷史市場反應幅度為"
                        f"{band_label(event.communication_band)}。"
                    )
                else:
                    info.write("此股票目前沒有可公開的受控事件情報。")
            else:
                info.caption("此股票目前沒有可公開的受控研究訊號。")
            action.button(
                "分析",
                key=f"analyse-{holding['ticker']}",
                width="stretch",
                on_click=_open_ticker_page,
                args=("股票分析", holding["ticker"]),
            )
    st.info("健檢只整合 Demo 持股與可用的受控研究訊號，不代表當前市場狀態或投資建議。")
    st.button("查看研究證據", key="portfolio-research", on_click=_go_to, args=("研究成果",))


def _holdings() -> list[BrowserDemoHolding]:
    value = st.session_state.setdefault(HOLDINGS_STATE_KEY, [])
    return [dict(item) for item in value]


def _render_intelligence_page(evidence: HistoricalEvidenceFixture) -> None:
    st.markdown('<div class="eyebrow">FINANCIAL NLP</div>', unsafe_allow_html=True)
    st.title("金融情報")
    st.write(
        "這裡把「事件類型」、「後續市場反應幅度」與「文字情緒」分開呈現。"
        "三者不是同一件事，也不會合併成看似精確的單一分數。"
    )
    st.caption("顯示歷史外推事件視窗的公開安全衍生資訊，不是即時新聞。")
    by_ticker = {item.ticker: item for item in evidence.tickers}
    st.session_state.setdefault("intelligence_ticker", "2330")
    ticker = st.selectbox(
        "選擇事件研究股票",
        tuple(FROZEN_UNIVERSE),
        format_func=lambda value: (
            f"{value} {FROZEN_UNIVERSE[value]}"
            f"{' · 無可公開事件' if by_ticker[value].event is None else ''}"
        ),
        key="intelligence_ticker",
    )
    _render_event_card(by_ticker[ticker])
    _render_related_pages(ticker, key="intel-related")


def _render_event_card(item: TickerEvidence) -> None:
    event = item.event
    if event is None:
        st.info("此股票目前沒有可公開的受控事件情報；系統不補寫事件內容。")
        return
    with st.container(border=True):
        st.markdown(f"**{item.ticker} {item.company}｜{event.event_class}類重大訊息**")
        st.caption(
            f"事件時間 {event.published_at[:16].replace('T', ' ')} · "
            "重大訊息分類資料 · 受控歷史案例"
        )
        st.write(event.summary)
        event_col, reaction_col, sentiment_col = st.columns(3)
        event_col.markdown(f"**事件類型**\n\n{event.event_class}")
        reaction_col.markdown(f"**歷史市場反應幅度**\n\n{band_label(event.communication_band)}")
        sentiment_col.markdown("**中文文字情緒**\n\n不提供判定")
        st.info(
            f"如何閱讀：此事件的自動化反應幅度分數位於歷史樣本約第 "
            f"{event.historical_percentile:.1f} 百分位；這是幅度排序，不是漲跌方向。"
        )
        st.caption(
            "授權邊界：事件原文與標題不在公開 Demo 顯示範圍；"
            "摘要只由公司、日期、事件分類與聚合筆數等允許欄位確定生成。"
        )
        st.caption("中文文字情緒尚未通過獨立驗證，因此不輸出正面／中立／負面判定。")


def _render_research_results(release: PublicWebDemoReleaseConfig) -> None:
    st.markdown('<div class="eyebrow">RESEARCH EVIDENCE</div>', unsafe_allow_html=True)
    st.title("研究成果")
    st.markdown("### 研究問題如何演進")
    st.write(
        "最初把波動風險分成高／一般，但跨期實驗發現結果容易受門檻與市場狀態影響。"
        "因此最終改為預測連續的『個股相對波動異常程度』，保留更多訊息，也更符合實驗證據。"
    )
    st.markdown("### 價格與成交量模型")
    a, b, c, d = st.columns(4)
    a.metric("最終模型", "Ridge", border=True)
    b.metric("跨期測試", f"{release.track_a_outer_folds} 段", border=True)
    c.metric("平均排序相關", f"{release.track_a_mean_outer_spearman:.4f}", border=True)
    d.metric("平均 R²", "-0.009", border=True)
    st.write(
        "最高預測分組的實際波動異常平均為全體的約 "
        "1.3542 倍（top-decile lift）；mean outer MAE 為 0.5473。證據主要在跨期相對排序；"
        "R² 接近零，因此不宣稱能精準預測振幅，更不預測方向。"
    )
    st.caption(
        "Track A｜10 檔 · 20,637 筆 historical OOS rows · 7 個 rolling-origin outer periods。"
        "Inner temporal selection 與前處理均限制在各 outer fold 的較早訓練資料內。"
    )
    st.markdown(
        f"[時序評估證據]({EVIDENCE_BASE_URL}/research/evaluation/f5_nested_temporal_evaluation_result.md)"
        f" · [排序與穩健性]({EVIDENCE_BASE_URL}"
        "/research/evaluation/f6_ranking_robustness_result.md)"
        f" · [模型選擇紀錄]({EVIDENCE_BASE_URL}"
        "/research/evaluation/f7_final_research_model_result.md)"
    )
    left, right = st.columns(2)
    left.image(
        str(ROOT / "docs/assets/track_a_model_comparison.svg"),
        caption="三種候選模型的歷史外推比較",
        width="stretch",
    )
    right.image(
        str(ROOT / "docs/assets/track_a_ridge_deciles.svg"),
        caption="預測分數分組與實際波動異常的關係",
        width="stretch",
    )
    with st.expander("模型選擇與驗證細節"):
        st.write(
            "比較 Persistence、Ridge 與 HistGradientBoosting。Ridge 與樹模型落在預先凍結的"
            "0.01 Spearman practical-tie margin 內，最後依較低平均 MAE 的既定 tie-break "
            "選擇 Ridge（alpha=100），不代表 Ridge 在所有指標全面勝出。"
        )
        st.write("所有評估使用七段 rolling-origin 時序外推；每一段的前處理與模型只用較早資料擬合。")
    st.markdown("### 金融 NLP 與事件情報")
    x, y = st.columns(2)
    x.metric("事件資訊的反應幅度排序相關", "0.2504", border=True)
    y.metric("高分組反應幅度", "1.623×", border=True)
    st.caption(
        "Track B｜7,582 events → 3,433 reaction windows · 9 檔 · chronological OOF。"
        "此處評估 metadata-only 的 absolute market reaction，是歷史關聯，不是方向或因果。"
    )
    st.info("兩個 track 的研究問題、target 與評估協議不同，不能直接比較兩組 Spearman 誰更好。")
    st.markdown(
        f"[市場反應評估證據]({EVIDENCE_BASE_URL}/research/evaluation/b4_market_reaction_validation_result.md)"
        f" · [NLP 整合與能力邊界]({EVIDENCE_BASE_URL}"
        "/research/evaluation/b5_nlp_intelligence_integration_result.md)"
    )
    st.markdown(
        "- 已完成台灣金融語料的中文 BERT 領域適應；目前只主張文字表示能力。\n"
        "- 中文文字情緒尚未通過獨立驗證，因此不輸出正／中／負判定。\n"
        "- BERT 文字沒有為市場反應方向帶來穩健增益；這項負面結果完整保留。"
    )


def _render_architecture() -> None:
    st.markdown('<div class="eyebrow">ENGINEERING EVIDENCE</div>', unsafe_allow_html=True)
    st.title("系統架構")
    st.image(str(ROOT / "docs/assets/system_architecture.svg"), width="stretch")
    web, backend = st.columns(2)
    with web.container(border=True):
        st.markdown("#### 公開 Web 展示路徑")
        st.write("瀏覽器 → Streamlit → 歷史 OOF 快照／衍生 metadata／session 持股")
        st.caption("零 runtime secret、零 request-time provider call；不是即時模型服務。")
    with backend.container(border=True):
        st.markdown("#### 研究與應用層")
        st.write("離線資料管線 → 研究 artifacts → FastAPI 版本化 contract")
        st.caption("此路徑與 LINE sandbox 的 PostgreSQL 不在公開 Streamlit request path 中執行。")
    st.markdown("### 實驗性 LINE 多通路原型")
    st.code(
        "LINE Demo OA → Cloudflare 安全邊界 → Google Apps Script\n"
        "→ FastAPI → PostgreSQL / Neon → GAS Flex Message → LINE",
        language="text",
    )
    st.caption(
        "此路徑用來證明 raw webhook 驗證、HMAC、GAS 呈現、FastAPI 串接、"
        "冪等寫入與使用者隔離；LINE 不是主要作品入口。"
    )
    st.markdown("### 未來外部驗證資料路徑")
    st.code(
        "TWSE / TPEx 官方資料 → 排程蒐集 → 私有不可變 raw archive\n"
        "→ lineage / manifest → 未來 unseen-data validation",
        language="text",
    )
    st.caption("蒐集資料不會觸發自動重訓，也不會進入目前公開 Demo 的 request path。")
    with st.expander("查看實際技術堆疊"):
        st.write(
            "Streamlit · FastAPI · PostgreSQL / Neon · LINE Messaging API · Google Apps Script · "
            "Cloudflare Worker / R2 · GitHub Actions · scikit-learn Ridge / "
            "HistGradientBoosting · BERT-base-Chinese"
        )


def _render_limitations(
    release: PublicWebDemoReleaseConfig, fixture: ControlledDashboardFixture
) -> None:
    st.markdown('<div class="eyebrow">METHODS & LIMITATIONS</div>', unsafe_allow_html=True)
    st.title("限制與方法")
    st.warning("即時市場推論尚未啟用，因訓練與即時資料的完整特徵一致性尚未通過驗證。")
    st.markdown(
        "- 研究採回溯、避免未來資訊洩漏的時序外推評估；不是前瞻或外部獨立驗證。\n"
        "- 中文文字情緒目前尚未通過獨立驗證。\n"
        "- 市場反應幅度不是方向預測，也不是因果效果。\n"
        "- 公開 Demo 無即時供應商呼叫、真實持股、個人資料或秘密。"
    )
    st.caption("詳細 gate、版本 lineage 與工程原型狀態集中於「研究與系統說明」。")
    st.markdown("### Future External Validation")
    st.write(
        "TWSE／TPEx forward collection 正在累積自然產生、模型未見過的資料，未來可用於外部驗證；"
        "排程蒐集不等於自動重訓，尚未產生外部驗證結果，也不影響已完成的 v1.0 研究。"
    )


def _render_technical_notes(
    release: PublicWebDemoReleaseConfig, evidence: HistoricalEvidenceFixture
) -> None:
    st.markdown('<div class="eyebrow">RESEARCH & TECHNICAL NOTES</div>', unsafe_allow_html=True)
    st.title("研究與系統說明")
    st.write("本頁保留研究與工程證據；它們不是公開 Demo 的主要產品功能。")
    with st.expander("即時推論 gate 與 fail-closed 決策", expanded=True):
        st.write(
            f"目前 serving readiness 檢核通過 {release.current_market_gate_passed}/"
            f"{release.current_market_gate_total} gates；exact feature parity 為 "
            f"{release.exact_feature_parity_passed}/{release.exact_feature_parity_total}。"
        )
        st.write("因此 current-market inference 維持停用，公開版只呈現歷史 OOF 受控快照。")
    with st.expander("中文與英文 NLP 證據邊界"):
        st.write("中文情緒未通過獨立驗證，因此主頁只呈現事件本身與反應幅度，不輸出正／中／負。")
        st.write(
            "系統具有 pinned FinBERT pipeline 與歷史 sanity-check 證據，但目前沒有適合公開產品頁、"
            "且具完整來源脈絡的英文 intelligence item，因此英文 NLP 不作為主功能。"
        )
    with st.expander("版本、lineage 與資料邊界"):
        st.code(
            f"fixture_id={evidence.fixture_id}\n"
            f"track_a_evidence_sha256={evidence.track_a_evidence_sha256}\n"
            f"track_b_evidence_sha256={evidence.track_b_evidence_sha256}",
            language="text",
        )
        st.write("原始授權事件標題／全文、私人資料與 provider credentials 均未打包。")
    with st.expander("實驗性整合與未來驗證"):
        st.write(
            "LINE／GAS／Cloudflare／FastAPI／PostgreSQL 路徑保留為多通路安全整合原型；"
            "TWSE／TPEx forward collector 用於未來 unseen-data validation。"
        )
        st.write("排程蒐集不會自動重訓；上述能力不構成目前的即時使用者功能。")


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
          .block-container { padding: 3rem .8rem 2rem; }
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
