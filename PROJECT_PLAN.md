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

- **RQ1**：既有多語／中文金融 NLP 模型轉移到繁體中文台灣金融公告時表現如何？
- **RQ2**：台灣領域的事件／影響模型，能否改善正式公告的分類品質？
- **RQ3**：英文 FinBERT 與台灣金融文字訊號，能否在價格／成交量特徵之外改善短期方向預測？
- **RQ4**：歷史市場反應特徵能否在不造成資料洩漏的前提下提供額外增益？
- **RQ5**：哪些訊號群組在不同市場期間與 regime 仍維持穩定？

### 核心產品問題

> 系統能否把分散的持股、價格異常與財經新聞整理成一般投資人每天看得懂、能追溯來源的研究摘要？

---

## 2. 專案目標

### 必須完成

- 建立可重現的歷史行情與新聞資料管線。
- 對驗證通過的英文金融文字產生 Positive／Neutral／Negative 與連續情緒分數。
- 對台灣金融文字建立版本化事件類型與金融影響協定；模型未通過門檻前，不偽造正式中文 sentiment score。
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

- 標註資料保存來源 metadata、合法短文本、ticker、event type、impact label、review status 與 label version。
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

#### `sentiment_results`

- 僅保存通過語言／領域 gate 的正式 sentiment inference；目前正式路線是英文 ProsusAI/finbert。
- `article_id`
- `ticker`
- `positive_prob`
- `neutral_prob`
- `negative_prob`
- `sentiment_score`
- `model_version`

#### `taiwan_financial_text_results`（規劃）

- `article_id`
- `ticker`
- `event_type`
- `impact_label`：`POSITIVE`／`NEUTRAL`／`NEGATIVE`／`AMBIGUOUS`
- `impact_probabilities`／`confidence`：僅在模型與校準協定支援時保存
- `model_version`
- `taxonomy_version`
- `inference_status`
- `unsupported_reason`

此表不得要求未驗證的正式中文 sentiment score。事件類型與 impact 是獨立欄位，避免將語氣中性的重大訊息強迫解讀成情緒。

#### `market_reaction_targets`（規劃）

- `ticker`
- `event_time`
- `information_cutoff`
- `reaction_start`
- `reaction_end`
- `return_horizon`
- `stock_return`
- `benchmark_return`
- `abnormal_return`
- `target_version`
- `market_snapshot_sha256`

此表是離線研究 target 與歷史統計，不是事件發生當下可直接使用的未來資訊。

#### `daily_features`

- `ticker`
- `feature_date`
- 價格、成交量、波動度、技術指標
- 全語言新聞數量、英文情緒、台灣事件／impact 與歷史市場反應統計；各群組可獨立缺值與消融
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
- 台灣標註資料按時間、來源事件與近似文本群組切分；不可讓同一公告或近似改寫跨 train／validation／test。

---

## 9. 模型與實驗設計

### 實驗組別

| 實驗 | 特徵 |
|---|---|
| Baseline 0 | 前一日方向或多數類別 |
| Baseline 1 | 價格＋成交量＋技術指標 |
| Model 2 | Baseline 1＋新聞數量 |
| Model 3 | Baseline 1＋英文 FinBERT sentiment |
| Model 4 | Baseline 1＋台灣金融 event／impact signal |
| Model 5 | Baseline 1＋歷史 market-reaction features |
| Model 6 | Baseline 1＋所有已驗證文字／事件／反應訊號 |
| Ablation | 分別移除英文情緒、台灣事件、市場反應與各 rolling feature group |

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

## 13. Milestones 0–12

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
- 12 筆人工英文樣本約 83.33% accuracy 只標示為 sanity／pipeline validation，不作正式 benchmark。

### M5.1 — Taiwan／Chinese Model Diagnostic（已完成）

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

### M6 — Feature 與 Label Foundation（已完成工程骨架）

工作：

- 建立價格、成交量、技術與已驗證英文情緒特徵。
- 建立 `t+1` label。
- 固定 information cutoff。
- 產出版本化 modeling dataset。

驗收：

- leakage tests 通過。
- feature definition 與資料字典完成。
- 任一 dataset snapshot 可由設定重建。
- 未驗證中文 sentiment 不填 neutral 或零；後續 M6.4 再納入通過 gate 的台灣訊號。

### M6.1 — Taiwan Financial Annotation Protocol（下一個最小里程碑）

工作：

- 撰寫 annotation guideline、inclusion／exclusion criteria 與合法短文本保存規則。
- 版本化 event taxonomy 與 `POSITIVE`／`NEUTRAL`／`NEGATIVE`／`AMBIGUOUS` impact rules。
- 收錄明確、模糊、需上下文與不可判斷案例；允許 abstain，不強迫三分類。
- 定義 reviewer／adjudication／quality-control 流程與標註一致性指標。
- 保存 source metadata、label version 與 licensing／copyright lineage。
- 定義依時間、事件群組與近似文本去重的 leakage-safe train／validation／sealed-test protocol。
- 稽核候選公開繁中金融資料；不得因資料卡聲明而跳過來源、重複與 split leakage 檢查。

驗收：

- 標註規範、schema、taxonomy version 與 QC checklist 可獨立審查。
- 30 筆 TWSE 診斷集維持 frozen diagnostic artifact，不作訓練或調參。
- 沒有生成假人工標籤，沒有啟動昂貴模型訓練。
- 下一階段資料需求、人工 review 範圍與授權風險有明確 go／no-go 結論。

### M6.2 — Taiwan Financial Text Model

工作：

- 以 MacBERT 或 validation 選出的適合中文 encoder 建立 event／impact baseline；不得預設 MacBERT 成功。
- 只在 training split fine-tune，在 validation 選模型、threshold 與 calibration。
- 最終 test 完全封存，保存 model／tokenizer revision、taxonomy version、dataset hash、seed 與訓練設定。
- 與 M5.1 所有被拒絕模型進行公平比較，保留失敗結果。

驗收：

- 正式 adoption gate 至少維持 Macro-F1 ≥ 0.70 且必要類別 recall ≥ 0.60；若 taxonomy 改變，需先版本化並重新核准對應 gate。
- 報告每類 precision／recall／F1、confusion matrix、calibration、coverage／abstention 與 error analysis。
- 未通過時維持 unsupported，不輸出假正式中文 sentiment score。

### M6.3 — Historical Market Reaction Signal

工作：

- 依公告 timestamp 與交易日 cutoff 建立 next-session、1-day、3-day return 候選 target。
- 優先比較 benchmark／market-adjusted abnormal return。
- 以 ticker／session information set 處理同日多事件歸因限制。
- 保存 target version、reaction window、market snapshot hash 與完整 timestamp lineage。

驗收：

- future return 只存在 label／target 端，leakage audit 證明不會流入事件當下 features。
- 所有 threshold、beta 或 normalisation 只由 train fit。
- market reaction 與 textual sentiment 在資料模型、報告與產品文案中明確分離。

### M6.4 — Integrated Feature Dataset Revision

工作：

- 延伸 M6 dataset，分別加入全語言新聞數量、英文 FinBERT、台灣 event／impact 與歷史 reaction feature groups。
- 加入 language／scored coverage、missing reason 與各訊號 availability indicators。
- 重新產生版本化 modeling snapshot；保留 M6 `features-v1` 作基準，不覆寫歷史資料集。

驗收：

- 每個 signal group 可獨立啟用、缺值、查核與消融。
- 相同 config 與 upstream snapshots 可重現 dataset hash。
- 所有 feature timestamp 不晚於 information cutoff。

### M7 — Downstream Prediction Experiments

工作：

- 訓練 majority／previous-direction baseline。
- 訓練只含市場特徵的模型。
- 依實驗矩陣分別加入新聞數量、英文情緒、台灣事件／impact、歷史市場反應與組合訊號。
- 執行時間切分與 walk-forward validation。
- 保存參數、指標與特徵重要性。

驗收：

- 有公平的同期間比較表。
- Test set 在模型選定前保持封存。
- 結果不只報 Accuracy。
- 可回答 RQ1–RQ5，並對市場 regime 與 signal-group ablation 提供結果。

### M8 — 回測與研究結論

工作：

- 定義訊號到部位的透明規則。
- 納入交易成本。
- 比較 buy-and-hold 與 benchmark。
- 計算報酬、drawdown、Sharpe 與 turnover。
- 撰寫限制與失敗案例。

驗收：

- 回測無 look-ahead bias。
- 回測只使用 out-of-sample prediction。
- 研究結論能回答英文情緒、台灣事件與市場反應是否各自有增益。
- 不因結果不顯著而隱藏負面結果。

### M9 — Prediction 與 Research API

工作：

- 載入鎖定模型 artifact。
- 提供 snapshot、news、sentiment、prediction API。
- 加入 model version 與 cutoff 回傳。
- 實作 Perplexity按需研究、快取與額度限制。

驗收：

- API 結果可追溯到資料與模型版本。
- 同 ticker／時間範圍可命中快取。
- LLM 失敗不影響既有行情與模型結果。

### M10 — LINE 整合與 GAS 瘦身

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

### M11 — 公開 Demo 與受控 Beta

工作：

- 建立使用範例資料的公開 Web Demo。
- 顯示近期價格、新聞來源、sentiment trend、模型訊號與歷史表現。
- 建立邀請制 LINE beta。
- 加入 rate limit、監控、隱私說明與資料刪除流程。

驗收：

- 未登入使用者看不到私人資料。
- Demo 不需要真實持股或私人 API key。
- 超過額度不會繼續產生付費呼叫。

### M12 — 最終封存、報告與部署

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
- Taiwan annotation import → validation → split isolation。
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
- Annotation agreement／duplicate-group split assertion。
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
- 標註先做 protocol、公開資料稽核與小型 pilot，再決定是否擴充，避免先投入大量人工或 GPU 成本。
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
| 中文新聞與英文 FinBERT 語言／領域不符 | 保留英文路線；M5.1 拒絕未過 gate 候選，另建台灣 event／impact protocol 與 encoder 實驗 |
| 正式公告語氣中性但事件具金融意義 | 將 event type、financial impact、textual sentiment 與 market reaction 拆成不同版本化概念 |
| 台灣標註不足或主觀 | 允許 AMBIGUOUS、建立 reviewer／QC／agreement 流程，sealed test 與 training 分離 |
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
- 研究：英文 sentiment 的驗證限制有文件；台灣支援通過 gate，或被明確標示 unsupported 且保留拒絕證據。
- 協定：台灣 event／impact taxonomy、標註／review、版本與 leakage-safe split 完整可稽核。
- 實驗：價格 baseline 與新聞數量、英文情緒、台灣事件、市場反應及組合訊號做公平同期間比較與消融。
- 回測：無前視偏誤，只使用 out-of-sample predictions，包含成本與 benchmark。
- 產品：LINE 能顯示個人持股、來源可追溯的研究訊號；文字情緒、事件 impact 與歷史市場反應不可混稱投資建議。
- 安全：無硬編碼 secrets、資料依使用者隔離、webhook 有簽章驗證。
- 公開：Demo 使用範例資料，受控 beta 有用量限制。
- 工程：測試、CI、migration、部署與文件完整。
- 溝通：不宣稱保證獲利，不將模型輸出包裝成直接投資建議。

---

## 18. 當前執行邊界

M0～M5.1 已完成並保留結果；M6 feature／label 工程骨架已完成驗證。現階段不得直接跳入 M7，也不得因中文模型不成熟而把所有中文資料填成 neutral。

下一個最小可執行里程碑是 **M6.1 Taiwan Financial Annotation Protocol**：

1. 建立 event taxonomy v1、impact label guide 與 AMBIGUOUS／abstain 規則。
2. 定義 inclusion／exclusion、來源／授權 metadata 與合法文本 retention。
3. 設計 reviewer、QC、agreement 與 label versioning。
4. 定義時間、事件群組及近似文本隔離的 train／validation／sealed-test protocol。
5. 稽核候選公開資料的來源、標籤、重複與 split leakage；不先訓練 MacBERT。

M6.1 完成並取得 go／no-go 決策後，才可進入 M6.2。GAS 在此期間維持既有功能，只作 LINE 過渡 adapter，不加入 NLP／ML 邏輯。
