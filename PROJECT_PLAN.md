# Financial AI Assistant — Project Plan

## 1. 專案摘要

### 專案名稱

**Financial AI Assistant：金融新聞情緒 × 股價研究 × LINE 持股助手**

### 專案定位

本專案不是「AI 報明牌」或自動交易系統，而是一套結合金融資料工程、NLP、機器學習與 LINE 互動介面的投資研究助手。

系統採雙軌設計：

1. **私人實用版**：保存真實持股、成本、個人推播與券商截圖辨識。
2. **受控公開研究版**：使用範例或匿名資料，展示新聞情緒、模型訊號、回測與系統架構；LINE Bot 僅開放受邀測試者。

### 核心研究問題

> 金融文字訊號與歷史市場反應訊號，是否能在價格、成交量與技術指標之外，提供可重現且無資料洩漏的短期股票方向預測增益？

本研究拆成五個問題：

- **RQ1**：既有多語／中文金融模型轉移到繁體中文台灣金融文字時表現如何？
- **RQ2**：在沒有人工標籤的情況下，台灣金融領域自適應能否改善文字 representation？
- **RQ3**：自動產生的 weak supervision 與 market-reaction labels 能否形成有用的台灣金融訊號？
- **RQ4**：這些台灣金融訊號能否在價格／成交量／技術特徵之外改善下游股票方向預測？
- **RQ5**：這些訊號在不同股票、事件類別、來源、市場期間與 regime 是否穩定？

### 核心產品問題

> 系統能否把分散的持股、價格異常與財經新聞整理成一般投資人每天看得懂、能追溯來源的研究摘要？

---

## 2. 專案目標

### 必須完成

- 建立可重現的歷史行情與新聞資料管線。
- 對驗證通過的英文金融文字產生 Positive／Neutral／Negative 與連續情緒分數。
- 對台灣金融文字建立零人工標注／零人工覆核的版本化自動訊號協定；不把 AI proxy 偽裝成正式中文 sentiment 或專家真值。
- 將文字情緒、台灣事件／影響、歷史市場反應與價格技術特徵分成可獨立消融的訊號群組。
- 建立價格基準、新聞數量、英文情緒、台灣事件、市場反應與組合模型。
- 以時間順序切分 Train／Validation／Test，避免資料洩漏。
- 完成模型評估、特徵比較與簡單回測。
- 建立 Python backend，提供持股、研究結果與每日摘要 API。
- 保留 LINE Bot 作為主要產品入口。
- 將原本 GAS 縮減為過渡期 LINE adapter，最終 webhook 可移至 Python。
- 支援每位使用者獨立的持股資料。
- 建立安全、限流、可觀測的小型公開測試版。

### 非目標

- 不做自動下單。
- 不保證報酬或宣稱預測必然準確。
- 不直接輸出「應買／應賣」的個人化投資指令。
- MVP 不做高頻交易、盤中 tick 預測或複雜量化組合最佳化。
- MVP 不支援所有國家與所有資產類別。
- 不把每一篇新聞全文都交給付費 LLM。

---

## 3. MVP 範圍

### 初始市場

- 以台股為主要研究市場。
- 先選 5～10 檔高流動性股票／ETF。
- 可包含台積電、0050 等代表性標的；最終名單需依資料完整性決定。

### 預測任務

第一版採二元分類：

> 使用交易日 `t` 收盤前已知的資料，預測 `t+1` 交易日報酬方向 Up／Down。

之後可延伸：

- 未來 3 日／5 日方向。
- 報酬率迴歸。
- Neutral zone 三分類。

### 公開測試規模

- 10～30 位受邀測試者。
- 每位使用者最多追蹤 10 檔股票。
- 每人每日最多 5 次即時 AI Research。
- 每日摘要最多推播一次；盤後摘要作為可選功能。

---

## 4. 系統架構

```text
LINE 使用者
    ↓
LINE Webhook
    ↓ 驗證 X-Line-Signature
FastAPI Backend
    ├── Auth / User Service
    ├── Portfolio Service
    ├── OCR / Smart Input Service
    ├── Research & Summary Service
    ├── Prediction Service
    └── LINE Flex / Push Adapter
             ↓
         PostgreSQL
             ↑
Scheduler / Worker
    ├── Market Data Ingestion
    ├── News Ingestion
    ├── Deduplication & Ticker Matching
    ├── English FinBERT Sentiment
    ├── Taiwan Event / Impact Inference
    ├── Historical Market Reaction Targets
    ├── Feature Pipeline
    ├── Daily Prediction
    └── Daily Brief Generation

Offline Research Pipeline
    ├── Dataset Snapshot
    ├── Time-based Split
    ├── Baseline Training
    ├── Taiwan Annotation Protocol
    ├── English / Taiwan Text Signal Evaluation
    ├── Historical Reaction Research
    ├── Signal-group Ablation
    ├── Backtesting
    └── Model Artifact / Experiment Report
```

### 過渡期架構

第一階段保留 GAS：

```text
LINE → GAS → Python API → GAS Flex Message → LINE
```

GAS 只負責：

- 接收與路由 LINE 事件。
- 呼叫 Python API。
- 發送 Reply／Push／Flex Message。

GAS 不再負責：

- 大量行情抓取。
- 新聞研究。
- Sentiment 與 ML。
- 多使用者資料交易。
- 長時間背景任務。

目標架構完成後，LINE webhook 直接進入 Python，以支援正式簽章驗證。

### 每日 Financial Intelligence Assistant 流程

```text
news / disclosures
→ deterministic deduplication + ticker matching
→ English FinBERT where validated
→ Taiwan event / impact model where validated
→ structured signal storage
→ market / volume / technical aggregation
→ research signal + source lineage
→ one compact daily portfolio brief
```

產品是 Financial Intelligence Assistant，不是 AI 選股神諭。日常大量處理使用 deterministic pipeline 與本機模型；Perplexity／LLM 只用於一次精簡摘要或使用者按需、具來源的「今天為何異動？」研究，不逐篇送出完整新聞。

---

## 5. 技術選型

| 領域 | 建議技術 |
|---|---|
| Backend | Python 3.12、FastAPI、Pydantic |
| Database | PostgreSQL；開發環境可使用 SQLite |
| ORM / Migration | SQLAlchemy、Alembic |
| Background Jobs | APScheduler 起步；部署後可用 Cloud Scheduler＋Cloud Run Job |
| Data Processing | Pandas 或 Polars、NumPy |
| NLP | Hugging Face Transformers、英文 FinBERT；台灣模型候選可含 MacBERT，但必須先驗證 |
| ML | scikit-learn、XGBoost 或 HistGradientBoosting |
| Experiment Tracking | MLflow 或結構化本地 artifacts |
| Backtesting | 自建透明回測模組；必要時再引入套件 |
| LINE | LINE Messaging API SDK |
| LLM Research | Perplexity，僅用於按需研究與最後摘要 |
| OCR / Parsing | Gemini API，輸出須經 Pydantic schema 驗證 |
| Testing | pytest、httpx、coverage |
| Deployment | Docker、Cloud Run；資料庫可用受管 PostgreSQL |
| Public Demo | Streamlit 或輕量 Web UI |
| CI | GitHub Actions |

技術選型可依免費額度與部署環境調整，但資料模型、API contract 與實驗規範不應依賴單一雲端供應商。

---

## 6. 資料來源策略

### 市場資料

- 先以現有 Yahoo Finance 來源完成原型。
- 將 provider 包裝成可替換 adapter。
- 正式公開前確認資料來源的使用條款、穩定性及展示權限。
- 每次 ingestion 保存來源、抓取時間與資料版本。

### 新聞與公告

優先順序：

1. 公司 IR／公開重大訊息。
2. 官方交易所或監管機構公告。
3. 合法 RSS／新聞 API。
4. Google News RSS 等索引來源，只保存必要 metadata 與原始連結。
5. Perplexity按需補充突發事件研究，不作為唯一歷史資料來源。

### 新聞紀錄欄位

- 標題
- 發布時間與時區
- 抓取時間
- 來源名稱
- 原始 URL
- 摘要或可合法保存的文字
- 關聯股票
- 去重 fingerprint
- 語言
- 英文 sentiment probabilities／score（僅限支援且已驗證的模型）
- 台灣事件類型／金融影響／ambiguous 狀態（通過協定後）
- inference status、unsupported reason、model／taxonomy version

### 標註與歷史市場反應資料

- 自動文字訊號保存來源 metadata、合法短文本、ticker、event／impact proxy、model／prompt provenance、agreement、abstention 與 signal version。
- 原始新聞全文不得因模型訓練需求而自動保存或提交；使用前必須確認來源與再利用條款。
- 歷史市場反應以事件發布時間為起點，建立 next-session、1 日或 3 日報酬／abnormal return target。
- 未來報酬只能作為歷史訓練 target／label，不能成為事件當下 prediction 的輸入。

---

## 7. 資料庫設計

### 核心資料表

#### `users`

- `id`
- `line_user_id_hash`
- `status`
- `created_at`
- `daily_research_limit`
- `daily_push_enabled`

#### `portfolios`

- `id`
- `user_id`
- `name`
- `is_demo`

#### `holdings`

- `id`
- `portfolio_id`
- `ticker`
- `name`
- `quantity`
- `cost_basis`
- `take_profit_pct`
- `stop_loss_pct`
- `updated_at`

#### `market_prices`

- `ticker`
- `trading_date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`
- `source`
- `ingested_at`

#### `news_articles`

- `id`
- `title`
- `published_at`
- `source`
- `url`
- `content_hash`
- `language`
- `ingested_at`

#### `article_tickers`

- `article_id`
- `ticker`
- `relevance_score`
- `match_method`

#### `english_sentiment_results`（邏輯名稱；現有實體表為 `sentiment_results`）

- 僅保存通過語言／領域 gate 的正式 sentiment inference；目前正式路線是英文 ProsusAI/finbert。
- `article_id`
- `ticker`
- `positive_prob`
- `neutral_prob`
- `negative_prob`
- `sentiment_score`
- `model_version`

#### `taiwan_text_signals`（規劃）

- `article_id`
- `ticker`
- `source_category`：官方來源原始 category，不被自動 taxonomy 覆寫
- `normalized_event_type`：自動推定的標準事件類別
- `event_type_source`：`official_metadata`／`deterministic_rule`／`model`／`llm`／`aggregate`
- `weak_label`：machine-generated event-impact／reaction proxy；不是 ground truth
- `weak_label_confidence`
- `agreement_score`／`vote_entropy`
- `abstained`／`abstention_reason`
- `encoder_version`
- `labeling_protocol_version`
- `model_revision`／`prompt_sha256`／`input_sha256`
- `generated_at`

此表不得保存或暗示人工驗證的正式中文 sentiment。官方 category、自動 normalized event、weak label 與 market reaction 必須分欄保存。

#### `market_reaction_labels`（規劃）

- `ticker`
- `article_id`／`event_group_id`
- `event_timestamp`
- `information_cutoff`
- `effective_session`／`anchor_session`／`reaction_end_session`
- `reaction_horizon`
- `raw_return`
- `benchmark_return`
- `abnormal_return`
- `reaction_class`：`POSITIVE_REACTION`／`NEUTRAL_REACTION`／`NEGATIVE_REACTION`
- `threshold_config`／`neutral_band`
- `protocol_version`
- `market_snapshot_sha256`
- `missing_reason`

此表是離線研究 target 與歷史統計，不是事件發生當下可直接使用的未來資訊。

#### `daily_features`

- `ticker`
- `feature_date`
- 價格、成交量、波動度、技術指標
- 全語言新聞數量、英文情緒、台灣 text representation、event metadata、weak supervision 與 past-only 歷史市場反應統計；各群組可獨立缺值與消融
- feature pipeline version

#### `predictions`

- `ticker`
- `as_of_time`
- `target_date`
- `prediction`
- `probability`
- `model_version`
- `available_information_cutoff`

#### `research_requests`

- `user_id`
- `ticker`
- `requested_at`
- `status`
- `cached_result_id`
- `estimated_cost`

---

## 8. NLP 與特徵工程

### 共用新聞處理流程

```text
抓取 metadata
→ URL／標題正規化
→ exact hash 去重
→ fuzzy title 去重
→ ticker／公司名稱配對
→ relevance scoring
→ 依語言、來源與驗證狀態路由
   ├── 英文 → pinned ProsusAI/finbert
   └── 台灣文字 → event／impact model（通過 gate 後）
→ 依股票、information cutoff 與交易日聚合
```

### A. 英文金融情緒訊號

- 固定 `ProsusAI/finbert` immutable revision，保留 Positive／Neutral／Negative probability 與 `positive_prob - negative_prob`。
- 12 筆人工樣本約 83.33% accuracy 只屬 pipeline sanity／回歸證據，不是正式研究 benchmark。
- 若未來需要英文正式 benchmark，必須另建較大、具代表性的封存資料集。
- 依 relevance 加權的 sentiment。
- 正／負面新聞比例。
- 情緒標準差。
- 最近 1／3／5 個交易日 rolling sentiment。
- 官方公告與一般新聞分開聚合。

### B. 台灣金融文字／事件訊號

本路線不是通用中文情緒替換器，而是針對繁體中文、台灣術語、TWSE 重大訊息與正式公司公告。語氣中性不代表事件沒有金融意義。

初始 event taxonomy：

- `EARNINGS`
- `REVENUE`
- `DIVIDEND`
- `BUYBACK`
- `CAPITAL_INCREASE`
- `CAPITAL_REDUCTION`
- `M&A`
- `REGULATORY`
- `MANAGEMENT_CHANGE`
- `GUIDANCE`
- `MATERIAL_TRANSACTION`
- `OTHER`

金融 impact labels：`POSITIVE`、`NEUTRAL`、`NEGATIVE`、`AMBIGUOUS`。無足夠上下文時必須允許 ambiguous，不可強迫三分類。taxonomy、label guide 與變更都要版本化。

MacBERT 可作未來 encoder 候選，但目前沒有成功結論；模型選擇必須經 validation-only 比較與 sealed test。

### C. 歷史市場反應訊號

```text
announcement timestamp
→ leakage-safe reaction window
→ stock return - benchmark／market return
→ historical market-reaction target
```

- 候選 target：next-session return、1-day abnormal return、3-day abnormal return。
- 同一 ticker／session 的多篇文章先視為共同 information set，不假裝能把單一日報酬精確歸因給每篇文章。
- market-reaction label 描述價格反應，不得重新命名為文字 sentiment。
- 任何以歷史反應建立的統計特徵，計算時只能使用 prediction timestamp 之前已完成的事件與報酬。

### D. 新聞數量與覆蓋狀態

- 全語言新聞篇數獨立於 sentiment inference 計算。
- 保存中文／英文、公告／一般新聞、scored／unsupported 數量。
- 保存 sentiment coverage ratio 與 missing／unsupported reason。
- 「沒有新聞」與「有中文新聞但正式模型尚未支援」不得使用相同語意。

### 價格與成交量特徵

- 1／3／5／20 日報酬。
- 5MA／20MA 與價格偏離。
- 成交量變化與 rolling z-score。
- 歷史波動度。
- RSI、MACD 等少量可解釋指標。
- 大盤或產業 benchmark 報酬。

### 防止資料洩漏

- 不可 random split。
- 預測某交易日時，只能使用當時已發布的新聞。
- 明確處理盤中、收盤後新聞歸屬。
- 所有 rolling feature 必須先 shift，再產生 label。
- scaler、imputer 與 feature selection 只能在 train fit。
- 每筆 prediction 保存 information cutoff。
- 事件發生後的 future／abnormal return 只能是歷史 training target、label，或由 prediction timestamp 之前已完成事件計算的歷史統計。
- future return 絕對不能成為該事件當下的 input feature；target 建構、feature availability 與 prediction cutoff 必須保存可稽核 lineage。
- 台灣自動訊號資料按時間、來源事件與近似文本群組切分；不可讓同一公告或近似改寫跨 train／validation／test。

---

## 9. 模型與實驗設計

### 實驗組別

| 實驗 | 特徵 |
|---|---|
| Baseline 0 | 前一日方向或多數類別 |
| Baseline 1 | 價格＋成交量＋技術指標 |
| Model 2 | Baseline 1＋新聞數量／deterministic metadata |
| Model 3 | Baseline 1＋英文 FinBERT sentiment |
| Model 4 | Baseline 1＋台灣 frozen text representation |
| Model 5 | Baseline 1＋official／inferred event metadata 與台灣 weak-supervision signals |
| Model 6 | Baseline 1＋past-only historical market-reaction features |
| Model 7 | Baseline 1＋所有可用文字／事件／weak／reaction 訊號 |
| Ablation | 分別移除英文情緒、台灣 text representation、weak supervision、historical reaction 與 event metadata |

### 候選模型

- Logistic Regression：主要可解釋 baseline。
- Random Forest：非線性比較。
- HistGradientBoosting／XGBoost：主要 tabular 候選模型。

MVP 不因追求複雜度而強制使用 LSTM／Transformer 做價格預測。英文 FinBERT 與未來驗證通過的台灣 encoder 提供 NLP／DL 成分；下游公平比較仍優先使用可解釋 tabular 模型。

### 切分方式

- Train：較早期間。
- Validation：後續完整期間，用於模型與 threshold 選擇。
- Test：最後完全封存期間，只在定案後評估。
- 補充 walk-forward validation，檢查時間穩定性。

### 評估指標

- Accuracy
- Precision
- Recall
- F1
- ROC-AUC
- Brier score／probability calibration
- Directional accuracy

### 無人工標籤的台灣訊號評估

- **Consistency**：跨模型／規則 agreement、vote entropy、coverage、abstention 與重跑一致性。
- **Predictive utility**：在相同期間與下游模型下，相對 Baseline 1 的 out-of-sample 增益。
- **Market-reaction prediction**：預測自動產生且完全隔離於事件當下 feature 的 reaction targets。
- **Robustness**：依股票、事件類別、來源、時期與 market regime 分層，並使用 walk-forward 與 bootstrap／block bootstrap。
- **Out-of-sample backtest**：只使用封存期預測，納入交易成本、turnover 與 benchmark。

上述評估衡量的是自動訊號的穩定性與預測用途；**predictive improvement 不等於 linguistic correctness，也不等於中文 sentiment 正確或因果成立**。

### 回測指標

- Cumulative return
- Annualized return
- Maximum drawdown
- Sharpe ratio
- Turnover
- 相對 buy-and-hold／market benchmark 表現

回測必須納入交易成本假設，且清楚標示為歷史研究結果，不構成未來績效保證。

---

## 10. API 初步契約

### 系統與使用者

- `GET /health`
- `POST /line/webhook`
- `POST /admin/users/{id}/approve`

### 持股

- `GET /users/{user_id}/portfolio`
- `POST /users/{user_id}/holdings`
- `PATCH /users/{user_id}/holdings/{holding_id}`
- `POST /users/{user_id}/portfolio-sync/preview`
- `POST /users/{user_id}/portfolio-sync/{operation_id}/confirm`

### 股票研究

- `GET /stocks/{ticker}/snapshot`
- `GET /stocks/{ticker}/news`
- `GET /stocks/{ticker}/sentiment`
- `GET /stocks/{ticker}/events`
- `GET /stocks/{ticker}/market-reaction`
- `GET /stocks/{ticker}/prediction`
- `POST /stocks/{ticker}/research`

### 排程與內部作業

- `POST /internal/jobs/market-data`
- `POST /internal/jobs/news`
- `POST /internal/jobs/sentiment`
- `POST /internal/jobs/taiwan-text`
- `POST /internal/jobs/market-reaction`
- `POST /internal/jobs/predictions`
- `POST /internal/jobs/daily-brief`

內部 endpoint 必須使用服務身分驗證，不得匿名公開。

---

## 11. 安全與隱私要求

### Milestone 0 前置事項

- 撤銷並輪替目前原始碼中的 LINE、Perplexity 與 Gemini 憑證。
- 新憑證只存於環境變數或 Secret Manager。
- `.env` 加入 `.gitignore`。
- 提供無真實值的 `.env.example`。
- 檢查原始碼備份 Google Doc 的分享權限與歷史版本。

### 公開版要求

- 驗證 LINE webhook signature。
- 每位使用者資料隔離。
- 對寫入操作使用 ownership check。
- 批次同步採 preview／confirm 與一次性 operation ID。
- 寫入交易需具備 idempotency。
- 加入 request rate limit 與每日 AI 額度。
- 不永久保存券商截圖；若需保存，必須取得明確同意。
- logs 不記錄 token、完整圖片或敏感持股內容。
- 提供刪除使用者資料的方法。
- 公開 Demo 只使用範例或匿名資料。

### 產品文案

所有公開介面標示：

> 本系統為學術研究與資訊整理工具，不構成投資建議；模型訊號與歷史回測不保證未來績效。

AI prompt 也必須遵守相同定位，不能一邊顯示免責聲明、一邊要求模型下達買賣命令。

---

## 12. Repository 結構

```text
financial-ai-assistant/
├── README.md
├── PROJECT_PLAN.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       └── repositories/
├── pipelines/
│   ├── market_data/
│   ├── news/
│   ├── sentiment/
│   └── features/
├── research/
│   ├── configs/
│   ├── training/
│   ├── evaluation/
│   └── backtesting/
├── jobs/
├── line_adapter/
├── gas_legacy/
│   └── README.md
├── demo/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── experiment_protocol.md
│   ├── privacy.md
│   └── deployment.md
└── artifacts/
    └── README.md
```

真實資料、模型大檔、API 回應快取與使用者持股不可直接提交 Git。

---

## 13. Milestones 0–17

### M0 — 安全處理與專案初始化

工作：

- 輪替所有外洩憑證。
- 建立新的 Git repository 與目錄骨架。
- 加入 `.gitignore`、`.env.example`、基本 README。
- 建立 Python、測試與格式化環境。
- 將原 GAS 存入私人備份，不提交含秘密的歷史版本。

驗收：

- Repository secret scan 無真實憑證。
- 測試指令可執行。
- CI 能完成 lint 與最小測試。

### M1 — FastAPI 與資料庫骨架

工作：

- 建立 FastAPI `/health`。
- 建立 SQLAlchemy models 與 Alembic migrations。
- 加入設定管理、結構化 logging 與統一錯誤格式。

驗收：

- 本機能啟動 API。
- migration 可從空資料庫建立 schema。
- API 與 DB 基礎測試通過。

### M2 — 多使用者持股服務

工作：

- 建立 users、portfolios、holdings。
- 加入 user ownership。
- 實作新增、修改、查詢。
- 實作 portfolio sync preview／confirm。
- 準備從 Google Sheet 匯入私人持股的一次性工具。

驗收：

- 兩位測試使用者無法互相讀寫資料。
- 重複 confirm 不會重複寫入。
- 批次同步失敗時不會留下半套資料。

### M3 — 歷史市場資料管線

工作：

- 建立 provider adapter。
- 抓取選定股票的 OHLCV。
- 正規化交易日、時區與股票代碼。
- 加入 retry、upsert、缺漏偵測。

驗收：

- 相同日期重跑不產生重複資料。
- 可輸出資料品質報告。
- 可用固定 snapshot 重現 feature。

### M4 — 新聞與公告管線

工作：

- 接入至少兩類來源。
- 保存 metadata、URL 與時間。
- 建立 exact／fuzzy 去重。
- 建立 ticker matching 與 relevance score。

驗收：

- 重複新聞不會重複計算。
- 每篇新聞能追溯原始來源。
- 對選定股票抽樣檢查配對品質。

### M5 — English FinBERT Baseline（已完成）

工作：

- 建立批次 inference。
- 保存三類機率、連續 score 與 model version。
- 建立每日 sentiment aggregation。
- 固定 ProsusAI/finbert revision，英文以外的文章明確標示 unsupported。

驗收：

- 同一模型與輸入可重現結果。
- 有人工抽樣 error analysis。
- sentiment 結果可依股票與日期查詢。
- 12 筆既有人工英文樣本約 83.33% accuracy 只標示為 **pipeline sanity check only**，不作正式 benchmark。

### M5.5 — Taiwan／Chinese Model Diagnostic（已完成）

工作：

- 比較中文詞典、yiyang Chinese FinBERT、bards.ai、Kenpache multilingual-v2 與本機翻譯後接英文 FinBERT。
- 使用 36 筆合成 regression set 與 30 筆 TWSE 公告衍生診斷集。
- 固定 adoption gate：Macro-F1 ≥ 0.70，且每個必要類別 recall ≥ 0.60。

驗收與正式決策：

- 中文詞典 Macro-F1 0.320。
- yiyang Chinese FinBERT Macro-F1 0.357。
- bards.ai 中文金融模型 Macro-F1 0.442。
- 翻譯＋ProsusAI FinBERT Macro-F1 0.592。
- Kenpache multilingual-v2 Macro-F1 0.640。
- 沒有候選通過 gate；這些結果是模型拒絕證據，必須保留，不得隱藏、覆寫或偽造改善。
- 正式中文 sentiment 維持 unsupported；30 筆診斷集不是 training dataset 或可發表 benchmark。

### M6 — Taiwan Dataset & Corpus Audit（已完成）

工作：

- 依治理表稽核 `tw-finance-159M`、FSC、MOPS／TWSE、FinMind-linked metadata、字典與其他候選來源。
- 對每個來源記錄 purpose、language、Taiwan relevance、labels、provenance、licence、可存取性、duplicate、split leakage 與 domain purity。
- 決策只使用 `ACCEPT`、`CONDITIONAL`、`HOLD`、`REJECT`；可下載不等於可訓練。
- 保留 Eland `HOLD / EXCLUDED FROM ACTIVE MODELING PIPELINE` 與全部拒絕證據；不得重審、救援或用於任何主動實驗。

驗收：

- `research/evaluation/taiwan_dataset_governance.md` 欄位完整且未知事項明確標示未驗證。
- 未通過來源、授權、重複與 leakage 稽核的資料不得進入訓練 corpus。
- 原文與大型資料只放在 Git 忽略路徑，公開報告只含統計、hash 與決策。

### M7 — Taiwan Financial Domain Adaptation（已完成；bounded pilot scope）

工作：

- 在 `ACCEPT` 或符合條件的 `CONDITIONAL` 無標籤台灣金融文本上進行 domain-adaptive pretraining 候選實驗。
- 比較 MacBERT 與其他適當中文 encoder；不預設 MacBERT 勝出。
- 保存 corpus snapshot hash、tokenizer／model revision、seed、訓練設定、licence 與成本。

驗收：

- 不使用人工標籤。
- 先以小型 feasibility run 驗證可重現性與資源需求，再批准大型訓練。
- domain-adapted encoder 只代表文字 representation，不宣稱 sentiment 正確性。

目前證據：FSC corpus builder 從 6,047 筆保留 6,021 筆，依 document-family 最新發布日切成
5,117 train／482 validation／422 sealed test，且 content／family hash 不跨 split。固定 revision
的 MacBERT-base 與 BERT-base-Chinese 先通過 2-step feasibility，再依批准的固定預算各完成
200-step pilot。兩者 gate 皆通過；因 vocabulary hash 相同，依預先指定的 final validation MLM
loss，BERT-base-Chinese 暫定為 frozen representation candidate。權重只在忽略路徑，test 未讀。
此決策不代表 sentiment 正確性，也不自動批准 full-corpus training。

### M8 — Automatic Market-Reaction Labeling

工作：

- 依 `docs/market_reaction_labeling_protocol.md` 對公告 timestamp 做時區與交易日對齊。
- 建立 next-session、1-day、3-day raw return、benchmark return、abnormal return 與 reaction class。
- 保存 event group、market snapshot、benchmark、threshold／neutral-band 與 protocol version。

驗收：

- future prices 只存在 target／historical weak-label 端，絕不成為事件當下 feature。
- threshold、beta、neutral band 與 normalization 只由 train／validation 決定，final test 封存。
- corporate action、缺價、同日多事件與 duplicate policy 均有自動化處理或明確 abstain。

### M9 — Weak-Supervision Signal Construction

工作：

- 建立字典、deterministic event rules、官方 category mapping、多語模型、翻譯＋FinBERT 與選配 LLM structured extraction labeling functions。
- 分開保存 official source category 與 automatically inferred normalized event type。
- 比較 reproducible weighted voting、confidence weighting 與 probabilistic／Snorkel-style aggregation。
- 輸出 weak label、confidence、coverage、agreement、vote entropy 與 abstention reason。

驗收：

- 任一 weak source 不得被當成真值；衝突不人工裁決。
- aggregation protocol、labeling-function revision、prompt hash 與 input hash 全部版本化。
- 付費 LLM 不作逐篇日常預設；大量處理優先 deterministic 或本機模型。

### M10 — Feature & Label Pipeline（市場／英文 v1 已完成，台灣延伸待完成）

工作：

- 保留已完成的價格、成交量、技術、英文 FinBERT、next-session label 與 `features-v1` snapshot。
- 新增台灣 frozen text representation、event metadata、weak-supervision signal 與 past-only reaction features。
- 加入 language、coverage、confidence、abstention、missing reason 與 availability indicators。

驗收：

- 既有 13:30 cutoff、盤後／週末歸下一 session、rolling shift 與 future-price mutation leakage tests 持續通過。
- announcement timestamp、future return、rolling window、duplicate article、same-event split 與 train／validation／test contamination 均有測試。
- 每個 feature group 可獨立啟用與消融，相同 config／snapshot 可重現 dataset hash。

### M11 — Downstream Prediction Experiments

工作：

- 訓練 majority／previous-direction baseline。
- 訓練只含市場特徵的模型。
- 依實驗矩陣分別加入新聞數量、英文情緒、台灣 text representation／event metadata、weak supervision、past-only market reaction 與組合訊號。
- 執行時間切分與 walk-forward validation。
- 保存參數、指標與特徵重要性。

驗收：

- 有公平的同期間比較表。
- Test set 在模型選定前保持封存。
- 結果不只報 Accuracy。
- 可回答 RQ1–RQ5，並對股票、事件類別、來源、期間與市場 regime 提供 robustness／ablation 結果。

### M12 — Backtesting & Research Conclusions

工作：

- 定義訊號到部位的透明規則。
- 納入交易成本。
- 比較 buy-and-hold 與 benchmark。
- 計算報酬、drawdown、Sharpe 與 turnover。
- 撰寫限制與失敗案例。

驗收：

- 回測無 look-ahead bias。
- 回測只使用 out-of-sample prediction。
- 研究結論能回答英文情緒、台灣 representation、weak supervision 與 market reaction 是否各自有增益。
- 不因結果不顯著而隱藏負面結果。
- 明確聲明下游預測改善不等於中文語意或 sentiment 正確性。

### M13 — Prediction & Research API

工作：

- 載入鎖定模型 artifact。
- 提供 snapshot、news、sentiment、prediction API。
- 加入 model version 與 cutoff 回傳。
- 實作 Perplexity按需研究、快取與額度限制。

驗收：

- API 結果可追溯到資料與模型版本。
- 同 ticker／時間範圍可命中快取。
- LLM 失敗不影響既有行情與模型結果。

### M14 — LINE Integration & GAS Slimming

工作：

- 保留既有 Flex Message UX。
- GAS 改為呼叫 backend。
- Gemini OCR 改為 preview／confirm API。
- 每位使用者取得自己的持股與摘要。
- 最終將 webhook 移到 Python 並驗證 signature。

驗收：

- LINE 可完成持股查詢、記帳預覽、確認與每日摘要。
- 不再從 GAS 直接呼叫 Perplexity。
- 不再於 GAS 原始碼保存 secrets。

### M15 — Public Demo & Controlled Beta

工作：

- 建立使用範例資料的公開 Web Demo。
- 顯示近期價格、新聞來源、sentiment trend、模型訊號與歷史表現。
- 建立邀請制 LINE beta。
- 加入 rate limit、監控、隱私說明與資料刪除流程。

驗收：

- 未登入使用者看不到私人資料。
- Demo 不需要真實持股或私人 API key。
- 超過額度不會繼續產生付費呼叫。

### M16 — Error Analysis & Robustness

工作：

- 分股票、事件類別、來源、期間與市場 regime 分析 coverage、abstention、錯誤與增益。
- 檢查 weak-source dominance、label-function correlation、embedding drift 與資料供應變動。
- 使用 bootstrap／block bootstrap 報告不確定性，保留所有失敗與不穩定期間。

驗收：

- 不依賴人工標籤宣稱語意 accuracy。
- 結果能指出訊號何時失效、缺值或應 abstain。
- robustness 報告可重現並連結 dataset／model／protocol hash。

### M17 — Final Portfolio / Report / Deployment

工作：

- 鎖定 final model、dataset snapshot 與 test report。
- 完成 README、架構圖、資料字典與實驗報告。
- 完成部署與 smoke test。
- 準備教授 Demo script、簡報素材與限制說明。

驗收：

- 新環境依 README 可重建專案。
- CI 全部通過。
- 公開 Demo 與受邀 LINE 流程可完整操作。
- 研究結果、產品功能與投資免責界線清楚。

---

## 14. 測試策略

### Unit Tests

- 股票代碼正規化。
- 張／股換算。
- 技術指標與 rolling feature。
- 新聞去重。
- ticker matching。
- sentiment aggregation。
- event taxonomy／impact schema／ambiguous handling。
- market-reaction window 與 abnormal-return target。
- label 與 information cutoff。
- API 額度計算。

### Integration Tests

- Market provider → database。
- News provider → dedup → sentiment。
- Taiwan automated-signal import → provenance validation → split isolation。
- Event timestamp → market-reaction target → leakage audit。
- OCR preview → confirm → holdings。
- Scheduled job → prediction → daily brief。
- LINE event fixture → Flex response。

### Research Validation

- Temporal split assertion。
- No future timestamps assertion。
- Train-only preprocessing assertion。
- Backtest signal lag assertion。
- Dataset and artifact checksum。
- Automated-label agreement／duplicate-group split assertion。
- Future reaction target excluded from contemporaneous feature assertion。
- Signal-group availability／ablation schema assertion。

### Deployment Checks

- Health check。
- Database migration。
- Missing secret handling。
- Provider timeout fallback。
- LINE signature rejection。
- Rate-limit behavior。

---

## 15. 成本控制

- 日常新聞抓取不使用 Perplexity逐篇搜尋。
- FinBERT 優先批次執行。
- 台灣 NLP 優先使用可本機批次執行的 encoder；大型 generative model 只作受控比較，不作逐篇日常預設。
- 自動文字訊號先做 protocol、公開資料稽核與小型 pilot，再決定是否擴充，避免不受控的 API 或 GPU 成本。
- 相同 ticker／日期的研究結果共用快取。
- 每人每日研究次數有限制。
- 每日摘要使用聚合結果，只進行一次 LLM synthesis。
- 所有付費呼叫保存實際 usage；不只依硬編碼費率估算。
- 設定每日與每月成本上限及自動停用開關。

---

## 16. 主要風險與因應

| 風險 | 因應方式 |
|---|---|
| 新聞授權或全文不能保存 | 優先保存 metadata、必要摘要與原始連結 |
| Yahoo 來源不穩定 | Provider adapter、快取與替代來源 |
| 中文新聞與英文 FinBERT 語言／領域不符 | 保留英文路線；M5.5 保留未過 gate 候選的拒絕證據，另建台灣 event／impact protocol 與 encoder 實驗 |
| 正式公告語氣中性但事件具金融意義 | 將 event type、financial impact、textual sentiment 與 market reaction 拆成不同版本化概念 |
| AI proxy 主觀、彼此不一致或自我驗證 | 允許 AMBIGUOUS／ABSTAIN、保存多模型 provenance 與 agreement；以 sealed market test 驗證下游增益，不宣稱語意真值 |
| 公開訓練資料來源或授權不明 | 使用前稽核來源、再利用權、重複與 leakage；不提交未確認授權的全文 |
| 用未來報酬造成 target leakage | future return 僅作離線 target；保存 reaction window 與 cutoff lineage，建立自動 leakage assertion |
| 新聞發布時間造成 leakage | 保存原始時區、定義 cutoff、盤後新聞歸下一交易日 |
| 少數人耗盡 API 額度 | 每人限流、快取、全域成本上限 |
| 持股隱私外洩 | user ownership、匿名化、敏感 log 遮蔽 |
| 模型沒有顯著提升 | 如實呈現負結果與 error analysis，仍具有研究價值 |
| 公開介面被理解為投資建議 | 文案、prompt 與 UI 都改為研究訊號及限制說明 |
| GAS 與 Python 過渡期重複邏輯 | 設定單一 source of truth，按 milestone 逐步移除 GAS 邏輯 |

---

## 17. Definition of Done

專案完成必須同時符合：

- 資料：歷史行情、新聞、英文情緒、台灣事件／impact、market reaction 與 features 可重現；不適用訊號有明確 unsupported／missing reason。
- 研究：英文 sentiment 的驗證限制有文件；台灣自動訊號通過 leakage-safe out-of-sample 增益 gate，或被明確標示 experimental／unsupported 且保留拒絕證據。
- 協定：台灣 event／impact proxy taxonomy、模型／prompt provenance、consensus／abstention、版本與 leakage-safe split 完整可稽核。
- 實驗：價格 baseline 與新聞數量、英文情緒、台灣事件、市場反應及組合訊號做公平同期間比較與消融。
- 回測：無前視偏誤，只使用 out-of-sample predictions，包含成本與 benchmark。
- 產品：LINE 能顯示個人持股、來源可追溯的研究訊號；文字情緒、事件 impact 與歷史市場反應不可混稱投資建議。
- 安全：無硬編碼 secrets、資料依使用者隔離、webhook 有簽章驗證。
- 公開：Demo 使用範例資料，受控 beta 有用量限制。
- 工程：測試、CI、migration、部署與文件完整。
- 溝通：不宣稱保證獲利，不將模型輸出包裝成直接投資建議。

---

## 18. 當前執行邊界

M0～M7 bounded pilot 已完成並保留結果；既有市場／英文 `features-v1` 工程骨架已完成驗證。下一執行單元是 M8 automatic market-reaction labeling；不得未經新理由直接擴大 M7 訓練，也不得因中文模型不成熟而把所有中文資料填成 neutral。

台灣路線的最終研究決策是 **Zero-Manual-Label Taiwan Financial Learning Protocol**：全程不使用人工標注、人工覆核、人工裁決或人工 sentiment ground-truth 建置。

1. 建立 event taxonomy v1、impact label guide 與 AMBIGUOUS／abstain 規則。
2. 定義 inclusion／exclusion、來源／授權 metadata 與合法文本 retention。
3. 設計 model/prompt provenance、QC、agreement、consensus、abstention 與 signal versioning。
4. 定義時間、事件群組及近似文本隔離的 train／validation／sealed-test protocol。
5. 稽核候選公開資料的來源、標籤、重複與 split leakage；不先訓練 MacBERT。

event taxonomy v1、impact／ambiguous guideline、版本化 schema、QC／split protocol 與資料稽核 CLI 已建立；正式自動訊號契約見 `docs/automated_chinese_text_signal_protocol.md`。Eland 的公開 viewer 初步顯示非金融內容混入，官方 raw split 下載回傳 HTTP 401，後續即時頁面檢查回傳 404；其永久文件角色為 **歷史候選資料集—HOLD／排除於主動建模流程**。不得重審、救援、使用快取或不明 mirror，也不得用於訓練、領域自適應、weak supervision、正式評估、特徵或 corpus 合併。

M6 不設人工 gold-label 門檻。最低門檻改為：來源與時間可追溯、授權／保存用途可核對、去重與 cutoff 稽核通過、模型／prompt／input hash 完整、無效輸出不偽裝 neutral、每個 feature group 可獨立消融，並以 chronological validation、sealed market test 與 walk-forward 驗證增益。所有 preprocessing、consensus rule 與 threshold 只能由 train／validation 決定。

第一批 60 筆 TWSE calibration 已以 60 個不同 ticker 建立。2026-08-26 完成一輪
Gemini 3.1 Pro Reviewer A 與 Codex Reviewer B 的獨立 AI-to-AI 診斷：impact raw agreement 0.766667、
kappa 0.640411；event raw agreement 0.650000、kappa 0.533679。因 event 未達 0.60，決策為
歷史 agreement CLI 產生 `PAUSE_AND_REVISE_GUIDELINE`，但專案已改採零人工路線。這一輪只
作模型穩定性與 prompt/taxonomy 診斷，不是 gold set，也不作 supervised truth。衝突不人工
裁決，而是保留為 disagreement／AMBIGUOUS／ABSTAIN metadata。

M6 主動來源與 corpus 稽核已記錄於 `research/evaluation/taiwan_active_source_metadata_audit.md` 與 `research/evaluation/fsc_official_archive_audit.md`：TWSE OpenAPI 接受作官方 ingestion／metadata；FinMind `TAIEX` total-return index 接受作非商用研究 benchmark；FinMind news 僅 conditional metadata，尚不得直接建立 reaction event；`tw-finance-159M` 與衍生 `tw-fsc` corpus 維持 HOLD。取得批准後，FSC 五個官方 archive 只下載到 Git 忽略位置並通過自動稽核；builder 保留 6,021 筆 family-isolated corpus。M7 的兩步 feasibility 與固定 200-step bounded pilot 均完成，兩候選皆通過 gate；相同 vocabulary 下依預先 final-loss 規則推薦 BERT-base-Chinese 作 frozen representation candidate。權重僅存在忽略路徑，sealed test 未讀，且不宣稱 sentiment 品質。下一個最小可執行單元是 M8 automatic market-reaction labeling。Eland 不在工作佇列，只保留 HOLD／排除記錄。GAS 維持既有功能，只作 LINE 過渡 adapter，不加入 NLP／ML 邏輯。
