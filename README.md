# Financial AI Assistant

結合金融新聞情緒、股票價格特徵、機器學習、回測與 LINE 持股助手的研究型 Financial AI 專題。

## 核心研究問題

加入金融新聞情緒特徵後，是否能改善只使用價格、成交量與技術指標的短期股票方向預測？

## 產品定位

- 私人實用版：未來可在受保護的環境保存真實持股與成本，並整合 LINE 推播及券商截圖辨識。
- 受控公開研究版：只使用範例、合成或匿名資料，展示新聞情緒、模型訊號、回測結果與系統架構。

目前狀態：**M5 FinBERT sentiment pipeline / early development**。M0～M2 已建立安全基礎、FastAPI、SQLAlchemy/Alembic 與多使用者持股服務；M3 加入歷史日線 OHLCV；M4 加入 TWSE 官方新聞／公告管線；M5 建立固定模型 revision 的英文 FinBERT 批次推論、每日聚合與可重現 error analysis。ML 預測與前端 Demo 尚未實作。

## 預計系統架構

目前 FastAPI 提供健康檢查與具 ownership 邊界的持股 API，SQLite 作為本機預設資料庫，PostgreSQL 為部署目標。後續資料管線將分別擷取市場與新聞資料，產生情緒、價格、成交量及技術指標特徵；研究模組負責訓練、時間序列評估與回測；LINE adapter 維持在服務邊界，避免私人資料進入公開研究資料集。

## 本機安裝

需要 Python 3.12 與 Git。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
```

如需本機設定，請複製 `.env.example` 為 `.env`，並只在本機填值；`.env` 不可提交。

## 啟動 API

```bash
uvicorn backend.app.main:app --reload
```

健康檢查位於 `GET http://127.0.0.1:8000/health`。

## M2 持股 API

第一迭代提供：

- `GET /users/{user_id}/portfolio`
- `POST /users/{user_id}/holdings`
- `PATCH /users/{user_id}/holdings/{holding_id}`
- `POST /users/{user_id}/portfolio-sync/preview`
- `POST /users/{user_id}/portfolio-sync/{operation_id}/confirm`

過渡期 API 要求 `X-User-ID` 與路徑中的 `user_id` 相同，以測試 ownership 隔離。這不是公開環境的最終身份驗證；依 PROJECT_PLAN，M10 必須改由通過 LINE signature 驗證的 backend 身分提供 user context。

批次同步先建立 15 分鐘有效的一次性 operation，再由 confirm 原子套用。重複 confirm 不會重複新增持股。

## 一次性私人持股匯入

先從私人 Google Sheet 手動匯出 CSV；不要讓工具連線或保存 Sheet ID。輸入 CSV 必須放在 Git 已忽略的 `imports/` 目錄，欄位為：

```text
ticker,name,quantity,cost_basis,take_profit_pct,stop_loss_pct
```

工具只接受 SHA-256 格式的 LINE user ID hash，不接受或保存原始 LINE ID；預設僅驗證：

```bash
python -m scripts.import_holdings imports/holdings.csv \
  --line-user-id-hash "<64-character-lowercase-sha256>"
```

人工確認驗證結果後才可加上 `--apply`。不得把 CSV、真實持股或匯入後的本機資料庫提交 Git。

## M3 歷史市場資料

範例 universe 位於 `research/configs/market_universe.example.json`。執行前必須先完成 migration：

```bash
alembic upgrade head
python -m jobs.market_data \
  --config research/configs/market_universe.example.json \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --snapshot artifacts/market-prices-2025.json
```

Yahoo 只是可替換的原型 provider。每次 ingestion 保存 provider、日期範圍、抓取時間、筆數與品質報告；相同 ticker／日期／來源重跑會更新同一列，不產生重複資料。

品質報告中的 `potential_missing_weekdays` 只是候選缺漏，仍需用台股交易日曆排除國定假日。Snapshot 依排序後的標準 OHLCV 計算 SHA-256，不包含會隨執行改變的 ingestion timestamp。

## M4 新聞與公告資料

M4 僅使用公開的 TWSE 官方來源：上市公司每日重大訊息 OpenAPI 與 TWSE 新聞 RSS。RSS 只保存必要 metadata、原始連結與最多 500 字元的純文字短摘要，不保存原始 HTML 或全文。

```bash
alembic upgrade head
python -m jobs.news --source all \
  --aliases research/configs/ticker_aliases.example.json
```

每個來源各自產生 ingestion run。重大訊息的官方公司代號具有最高配對信度；一般新聞使用設定檔中的公開 ticker／公司別名進行可解釋配對。去重先比較標準化 identity hash，再於相近發布時間內比較標題相似度。Perplexity 不參與例行 ingestion。

## M5 FinBERT 情緒分析

NLP 依賴是選配，避免一般 API／CI 安裝大型模型：

```bash
python -m pip install -e ".[nlp]"
alembic upgrade head
financial-ai-sentiment
```

預設模型固定為 `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43`。每筆結果保存 positive／neutral／negative 機率、`positive - negative` 連續分數、input hash 與 model version；相同 article／ticker／model 重跑不會重複推論。

官方 model card 將此模型標示為英文模型，因此 `zh-TW` 新聞會明確跳過，不會被當成 neutral，也不會自動送往翻譯或 LLM。語言策略與後續中文替代模型驗證門檻見 `docs/sentiment_language_strategy.md`。

M5.1 已比較透明詞典、兩個中文金融 BERT、多語金融模型，以及本機翻譯後接英文 FinBERT。所有候選都未通過 TWSE context set 的採用門檻，因此目前仍不產生中文 sentiment。比較結果見 `research/evaluation/chinese_sentiment_model_comparison.md`。

執行人工樣本 error analysis：

```bash
financial-ai-sentiment-audit \
  --output artifacts/finbert-manual-error-analysis.json
```

重跑 M5.1 比較（需要已下載的本機模型）：

```bash
financial-ai-chinese-sentiment-benchmark \
  --samples research/evaluation/twse_announcement_sentiment_samples.json \
  --local-files-only \
  --quiet \
  --output artifacts/chinese-sentiment-benchmark.json
```

## 測試與品質檢查

```bash
pytest
pytest --cov=backend --cov=pipelines.market_data --cov=pipelines.news --cov=pipelines.sentiment --cov-report=term-missing
ruff check .
python scripts/check_secrets.py .
```

## 安全與秘密管理

Repository 不得包含真實 API key、token、使用者 ID、試算表／文件 ID、真實持股、券商截圖或個人資料。秘密只應透過未追蹤的本機 `.env` 或部署平台的秘密管理服務注入。公開研究資料必須是範例、合成或完成匿名化的資料。外部憑證與舊 Google Doc 的人工安全事項記錄在 `docs/m0_security_checklist.md`。

## 聲明

本專案僅供學術研究與軟體工程展示，不構成投資建議、招攬或任何報酬保證。模型訊號與回測結果不代表未來績效。
