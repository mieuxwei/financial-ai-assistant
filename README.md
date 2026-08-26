# Financial AI Assistant

結合金融新聞情緒、股票價格特徵、機器學習、回測與 LINE 持股助手的研究型 Financial AI 專題。

## 核心研究問題

加入全自動金融文字訊號後，是否能改善只使用價格、成交量與技術指標的短期股票方向預測？

## 產品定位

- 私人實用版：未來可在受保護的環境保存真實持股與成本，並整合 LINE 推播及券商截圖辨識。
- 受控公開研究版：只使用範例、合成或匿名資料，展示新聞情緒、模型訊號、回測結果與系統架構。

目前狀態：**M6 Taiwan dataset/corpus audit in progress / zero-manual-label protocol approved**。M0～M2 已建立安全基礎、FastAPI、SQLAlchemy/Alembic 與多使用者持股服務；M3～M5 完成歷史日線、TWSE 新聞／公告與英文 FinBERT；M5.5 保留五個中文候選未通過舊標籤 gate 的結果；既有市場／英文 `features-v1` 已建立防止前視偏誤的價格、成交量、技術、已驗證英文情緒特徵與 `t+1` label。台灣路線採零人工標注／零人工覆核：中文輸出只作 automated silver signals，主要驗證改由時間序列外樣本增益、coverage、abstention 與穩定性決定。協定見 `docs/automated_chinese_text_signal_protocol.md`。

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

歷史 M5.5 診斷已比較透明詞典、兩個中文金融 BERT、多語金融模型，以及本機翻譯後接英文 FinBERT。所有候選都未通過 TWSE context set 的採用門檻，因此目前仍不產生中文 sentiment。接下來的台灣 NLP 路線會把 event type、financial impact、textual sentiment 與 historical market reaction 分開研究；MacBERT 只是待驗證候選，不是既定成功模型。比較結果見 `research/evaluation/chinese_sentiment_model_comparison.md`，後續協定見 `PROJECT_PLAN.md`。

執行人工樣本 error analysis：

```bash
financial-ai-sentiment-audit \
  --output artifacts/finbert-manual-error-analysis.json
```

重跑歷史 M5.5 診斷（需要已下載的本機模型）：

```bash
financial-ai-chinese-sentiment-benchmark \
  --samples research/evaluation/twse_announcement_sentiment_samples.json \
  --local-files-only \
  --quiet \
  --output artifacts/chinese-sentiment-benchmark.json
```

## M6 Feature 與 Label Dataset

M6 使用交易日 `t` 收盤時已知的資料預測下一個實際交易日方向。台股 information cutoff 預設為 Asia/Taipei 13:30；收盤後或非交易日發布的新聞歸到下一個交易日。至少需要 27 筆連續市場觀測才能產生包含 26 日 MACD 暖機與下一日 label 的資料列。

```bash
alembic upgrade head
financial-ai-features \
  --config research/configs/feature_pipeline.example.json \
  --snapshot artifacts/modeling-dataset.json
```

輸出保存完整設定、`features-v1`、market/sentiment snapshot hash 與 dataset SHA-256。相同輸入重跑會復用既有 dataset run。中文新聞沒有通過歷史 M5.5 採用門檻，因此對應 sentiment probability/score 保持 `null`；新聞數量則為 `0`，不會偽裝成 neutral sentiment。詳細定義見 `docs/feature_definitions.md`。

## M6 台灣金融資料集／語料稽核

事件 taxonomy、impact／ambiguous 規則與先前 AI-to-AI 診斷保留於 `docs/taiwan_financial_annotation_protocol.md`。正式研究路線不使用人工標注或人工覆核；自動訊號、consensus、abstention 與 leakage-safe 評估見 `docs/automated_chinese_text_signal_protocol.md`。候選外部資料只可放在 Git 忽略的 `.tools/` 或 `data/raw/`，不得提交原文。

JSON、JSONL、CSV 可直接稽核；Parquet 另安裝輕量選配依賴：

```bash
python -m pip install -e ".[audit]"
financial-ai-taiwan-dataset-audit --help
```

Eland 只保留為歷史候選資料集的拒絕證據，狀態固定為 **HOLD／排除於主動建模流程**；不得用於訓練、領域自適應、weak supervision、正式評估、特徵或 corpus 合併，也不在本里程碑追加救援或重審。主動來源決策見 `research/evaluation/taiwan_dataset_governance.md`，歷史稽核記錄見 `research/evaluation/eland_dataset_preliminary_audit.md`。

從本機已匯入的官方 TWSE 公告建立 60 筆未標注 calibration batch：

```bash
financial-ai-taiwan-calibration-batch \
  --limit 60 \
  --output artifacts/twse-calibration-batch.jsonl
```

輸出位置強制限制在 Git 忽略的 `artifacts/`、`.tools/` 或 `data/raw/`。工具會排除凍結的 M5.5 診斷文本、輪替不同 ticker、保留來源／時間／hash，並將所有標籤留空；不讀取或輸出未來報酬。

2026-08-26 本機校準準備已成功從 114 筆公開公告中選出 60 筆、涵蓋 60 個 ticker 的批次。Gemini 3.1 Pro Reviewer A 與 Codex Reviewer B 的獨立 AI-to-AI 診斷已完成：impact kappa 為 0.640411，event kappa 為 0.533679。這些數值只衡量模型間一致性，不是人工標注證據、不是 gold set，也不作 supervised truth。它們只用於改良 prompt、taxonomy、consensus 與 abstention 規則。Aggregate 結果見 `research/evaluation/twse_calibration_round_1_result.md`。

以下命令只重現已完成的歷史 AI-to-AI 診斷，不是人工標注工作流，也不產生正式 ground truth：

```bash
python -m pip install -e ".[annotation]"
financial-ai-taiwan-annotation-agreement \
  --reviewer-a outputs/m6_1_calibration_20260826/twse_calibration_reviewer_a.xlsx \
  --reviewer-b outputs/m6_1_calibration_20260826/twse_calibration_reviewer_b.xlsx \
  --output artifacts/twse-calibration-agreement.json
```

Agreement report 只保存模型穩定性證據。無論 kappa 高低都不得把它當成人工一致性、語意 accuracy 或訓練真值；衝突依版本化規則保留為 disagreement、`AMBIGUOUS` 或 `ABSTAIN`。

## 測試與品質檢查

```bash
pytest
pytest --cov=backend --cov=pipelines.market_data --cov=pipelines.news --cov=pipelines.sentiment --cov=pipelines.features --cov-report=term-missing
ruff check .
python scripts/check_secrets.py .
```

## 安全與秘密管理

Repository 不得包含真實 API key、token、使用者 ID、試算表／文件 ID、真實持股、券商截圖或個人資料。秘密只應透過未追蹤的本機 `.env` 或部署平台的秘密管理服務注入。公開研究資料必須是範例、合成或完成匿名化的資料。外部憑證與舊 Google Doc 的人工安全事項記錄在 `docs/m0_security_checklist.md`。

## 聲明

本專案僅供學術研究與軟體工程展示，不構成投資建議、招攬或任何報酬保證。模型訊號與回測結果不代表未來績效。
