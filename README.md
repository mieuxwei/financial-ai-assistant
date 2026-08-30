# Financial AI Assistant

**基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統**

一套研究導向的台股 Financial Intelligence Assistant：以 leakage-aware temporal evaluation
預測下一交易日的**個股相對波動異常程度**，並整合事件分類、市場反應強度、金融文字表示、
FastAPI、Streamlit 與 LINE/GAS controlled demo。

> 本專案不預測上漲／下跌、不提供買賣建議、不保證未來波動，也不宣稱中文情緒已驗證。

![System architecture](docs/assets/system_architecture.svg)

## Portfolio highlights

- **Track A — COMPLETE / FROZEN**：Ridge Regression `alpha=100`，依預先凍結規則從
  Persistence、Ridge、HGB 中選出；模型未部署。
- **Track B — COMPLETE THROUGH B5**：市場反應強度維持 `AUTOMATED_SIGNAL_ONLY`；中文
  linguistic sentiment 與方向預測明確 abstain。
- **Track C — PORTFOLIO COMPLETE**：F10 FastAPI、F11A controlled Streamlit、F11B controlled
  LINE integration 設計與 migration-copy demo 已完成，全部未部署。
- **R1A — PUBLIC WEB DEMO DEPLOYED**：零秘密、fixture-only Streamlit public demo 已完成部署；
  公開 HTTPS smoke test 通過。
- **R1B — DEPLOYED**：獨立 LINE Public Beta 已透過 Security Edge、Demo GAS、FastAPI 與 Neon
  sandbox 上線；R1B-UX1 多持股 LIFF 編輯器已在本機完成，尚待 Demo LIFF 外部設定。
- **F11B-2A complete**：官方 current OHLCV 10/10，但 exact feature parity 僅 5/23；目前
  **6 of 9 gates PASS，current-market integration blocked**。
- **Research integrity**：最終研究是 retrospective、leakage-aware、hypothesis-informed；
  不把已檢視的歷史期間重新包裝成 pristine sealed test。

完整作品集故事、架構、成果、截圖與限制見
[Portfolio Guide](docs/portfolio_finalization.md)。

## Research question

> Can leakage-safe price, volume, volatility and market-context features forecast next-session
> volatility surprise relative to each stock's own historical volatility context?

Primary target：下一交易日絕對 adjusted-close log return，除以截至 feature session `t` 已知的
20-session 個股歷史波動。所有 predictor 僅能使用 cutoff 前資訊。

## Research evolution

1. 初始研究將 normalized risk 轉為 `HIGH_RISK / NORMAL`。
2. M7–M11 顯示 threshold 與 volatility regime 對 binary operating behavior 影響顯著。
3. M9 發現 aggregate raw outcome 與 conditioned outcome 存在 Simpson-type composition effect。
4. 較穩定的研究訊號是 stock-relative volatility surprise，而不是 unconditional absolute
   volatility。
5. 最終研究改為 continuous forecasting，使用 nested rolling-origin evaluation、ranking、decile
   與 robustness 分析。
6. 舊 binary 結果完整保留為 **Exploratory Research History**，不是被刪除的失敗實驗。

## Track A results

![Historical OOS model comparison](docs/assets/track_a_model_comparison.svg)

| model | mean outer Spearman | mean outer MAE | worst-fold Spearman | mean top-10% lift |
|---|---:|---:|---:|---:|
| Persistence | 0.0608 | 0.7274 | 0.0080 | 1.1766 |
| Ridge | **0.1940** | **0.5473** | 0.1091 | 1.3542 |
| HGB | 0.1863 | 0.5480 | **0.1349** | **1.3611** |

- 32,357 final eligible historical rows。
- 20,637 historical OOS rows、七個 rolling-origin outer folds。
- Ridge 與 HGB 落在 frozen 0.01 Spearman practical-tie margin；Ridge 依較低 mean MAE 決勝。
- 最終安全 JSON artifact 使用完整 23-feature contract、`log1p` target transform 與 20,637 筆
  historical OOF percentile reference。
- Point-forecast R² 平均接近零；正確定位是 modest historical ranking signal，而非精準振幅預測。

![Ridge pooled deciles](docs/assets/track_a_ridge_deciles.svg)

Pooled Ridge deciles 從 D1 realized mean 0.5413 上升至 D10 1.1395，adjacent steps 9/9；個別
期間並非全部完美單調，且這不是 prospective validation。

## Track B results

Track B 將 linguistic sentiment、event class、market reaction、financial representation 與
media-tone proxy 分開，避免用報酬反推情緒。

- B4 corrected private backfill：7,582 events、3,433 aggregated ticker-reaction windows、9 tickers。
- Metadata-only absolute-reaction model：OOF Spearman 0.2504、top-decile lift 1.623。
- Signed reaction：market-only 0.0349、metadata-only 0.0784、BERT text + metadata 0.0408。
- BERT text 對 signed reaction 沒有 robust incremental value；這個負面結果完整保留。
- Market reaction maturity：`AUTOMATED_SIGNAL_ONLY`，只代表歷史關聯強度，不是方向、因果或
  報酬預測。
- Chinese linguistic sentiment：`ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`；positive、neutral、
  negative probabilities 全部為 null。
- Direction：`ABSTAIN_DIRECTION_NOT_SUPPORTED`。
- B3.1 沒有找到可獨立接受的中文 P/N/N ground truth；沒有降低 gate、人工標注或偽造結果。
- eLAND 永久排除於 active modeling，只保留歷史 rejection evidence。

## Controlled product demo

![Controlled public Streamlit demo](docs/assets/public_web_demo_home.jpg)

畫面中的 2330、特徵、分數與事件都是 deterministic synthetic fixture。它們不是 live market
data、模型績效證據或真實投資訊號。

### Public Web Demo — R1A

Status：`PUBLIC_WEB_DEMO_DEPLOYED`

- Primary hosting：Streamlit Community Cloud。
- Topology：單一 fixture-only Streamlit app；不需要 FastAPI。
- Entrypoint：`demo/public_app.py`。
- Runtime secrets：零。
- Request-time provider calls：零。
- Public URL：[Streamlit controlled demo](https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/)；
  nested-entrypoint 修正已部署，公開首頁與四個展示分頁的 bounded smoke test 通過。

部署規格、平台比較、資料邊界與 rollback 步驟見
[R1A Public Web Demo Release](docs/public_web_demo_release.md)。

### LINE Public Beta — R1B

Status：`LINE_PUBLIC_BETA_DEPLOYED`；R1B-UX1：`READY_FOR_LIFF_EXTERNAL_SETUP`

- 新 Demo LINE OA → Cloudflare Worker raw-signature edge → 新 Demo GAS → FastAPI → managed
  PostgreSQL sandbox。
- raw LINE user ID 只在驗證成功的 Edge 中使用，後端僅接收 keyed-HMAC principal。
- 每位使用者最多 5 檔 frozen-universe Demo 持股，30 天 retention，可自行刪除。
- 新增、修改、刪除皆需 Preview/Confirm，並以 webhook event ID 做 backend idempotency。
- 不使用私人 Google Sheet、Gemini、Perplexity、TWMD raw data 或 current-market F7 inference。
- 只有既有 2330 controlled fixture 有研究數值；其他 ticker 明確 abstain，不製造假分數。

架構、維運與 LIFF 升級順序見
[LINE Public Beta Architecture](docs/line_public_beta_architecture.md) 與
[Manual Setup Checklist](docs/line_public_beta_setup.md)。新 LIFF 編輯器一次管理最多五檔，
仍保留原有文字輸入作為備援。

### FastAPI

- `GET /health`
- `POST /api/v1/research/volatility-surprise/predict`
- `GET /api/v1/research/intelligence/{ticker}`
- controlled LINE demo endpoint with local service authentication

Research API 驗證 exact contract 與 lineage；一般 request 不即時抓 provider、不呼叫 LLM，
也不回傳私人持股。

### Streamlit — F11A

- 預設 `CONTROLLED_OFFLINE`，只讀合成 fixture，零網路請求。
- 選配 `LOCAL_API` 只接受帶明確 port 的 loopback origin。
- 顯示 continuous score、percentile、communication band、事件情報與明確限制。

### LINE/GAS — F11B

- 六個凍結入口：股票分析、持股健檢、金融情報、匯入持股、新聞研究、設定。
- F11B-1A 只在 private migration copy 建立 parser/dispatcher 與 legacy compatibility。
- F11B-1B 是 LINE → migration-copy GAS → FastAPI → deterministic fixture → Flex 的 controlled
  read-only demo。
- 未修改 live webhook、trigger、Sheet schema、真實持股或 Desktop original GAS；未部署。

## F11B-2A current-market gate

F11B-2A 的正式 decision：

`OFFICIAL_OHLCV_AVAILABLE_BUT_ADJUSTED_PARITY_UNRESOLVED`

- TWSE current OHLCV：10/10 frozen tickers、最近 35 sessions 完整。
- 0050：TWSE 有 2026-08-28；先前缺日是 candidate-provider freshness 問題。
- TAIEX total-return：與 TWSE 官方值在 20/20 current overlap sessions 完全一致。
- Historical stock training source：Yahoo `indicators.adjclose`。
- Audited official corporate-action lineage 無法證明可重建 training-equivalent adjusted close。
- Raw OHLCV 亦不是 source-identical。
- Exact feature parity：5/23；updated gate：6/9。

因此 `NOT_READY_FOR_F11B_2`。不得改模型、降低 tolerance、fallback 舊日資料或把 controlled demo
寫成 live。詳見 [F11B-2A result](research/evaluation/f11b_official_current_market_parity_result.md)。

## Architecture boundary

Python/FastAPI 負責 ingestion、features、ML/NLP、identity、portfolio business rules、persistence、
lineage、abstention 與 audit logs。GAS 長期只保留 LINE webhook entry、minimal routing、reply/push
與 Flex rendering。`X-User-ID` 仍是 development-only contract，不是正式 authentication。

私人實用版與受控公開版保持分離：真實持股、券商截圖、credentials、私人 GAS、licensed TWMD
raw records 與個人資料不得進入 public Git。

## Local installation

需要 Python 3.12 與 Git。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,demo]"
```

若需本機設定，複製 `.env.example` 為 `.env`；不得提交 `.env` 或印出其中內容。

### Run FastAPI

```bash
python -m uvicorn backend.app.main:app --reload
curl http://127.0.0.1:8000/health
```

### Run the controlled Streamlit demo

```bash
python -m streamlit run demo/app.py
```

保持預設「受控離線示範」即可進行無網路作品展示。

### Tests and lint

```bash
python -m pytest -q
ruff check .
python scripts/check_secrets.py
git diff --check
```

## Research integrity and limitations

- Retrospective、hypothesis-informed；不是 prospective 或 independent external validation。
- 十檔 frozen universe 與 documented temporal exclusion concentration 限制泛化能力。
- Track A 的主要價值是 ranking，不是 exact magnitude 或 direction。
- Track B reaction magnitude 是 observational association，不是 causal impact。
- 中文 sentiment 尚未驗證，正常行為是 abstain。
- English FinBERT eligibility 不代表 controlled fixture 已執行模型。
- F9/B6 optional NLP incremental-value study 未執行，且不是完成條件。
- Current-market serving 被 parity gate 阻擋；所有公開 demo 都是 controlled fixture。
- 本系統為學術／作品集研究，非投資建議。

## Documentation map

- [Portfolio guide](docs/portfolio_finalization.md)
- [Project plan](PROJECT_PLAN.md)
- [Authoritative handoff](HANDOFF.md)
- [Architecture](docs/architecture.md)
- [Final study protocol](docs/final_volatility_surprise_study_protocol.md)
- [F5 temporal evaluation](research/evaluation/f5_nested_temporal_evaluation_result.md)
- [F6 ranking robustness](research/evaluation/f6_ranking_robustness_result.md)
- [F7 final model](research/evaluation/f7_final_research_model_result.md)
- [B5 NLP integration](research/evaluation/b5_nlp_intelligence_integration_result.md)
- [F11A dashboard](research/evaluation/f11_dashboard_demo_result.md)
- [F11B controlled LINE demo](docs/f11b_controlled_line_demo.md)
- [F11B-2A parity audit](research/evaluation/f11b_official_current_market_parity_result.md)
- [R1A public web demo release](docs/public_web_demo_release.md)
- [R1B LINE public beta architecture](docs/line_public_beta_architecture.md)
- [R1B manual setup](docs/line_public_beta_setup.md)
- [Privacy](docs/privacy.md)
- [Deployment boundary](docs/deployment.md)
