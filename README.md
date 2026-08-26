# Financial AI Assistant

**Stock Volatility Risk Prediction with Financial NLP Intelligence**

中文工作名稱：**股票異常波動風險預警 × 金融 NLP 情報系統**。

這是一套結合市場資料工程、下一交易日異常波動風險預測、金融 NLP 情報、事件研究與 LINE
互動介面的研究型 Financial Intelligence Assistant。

## 核心研究問題

在嚴格避免資料洩漏的時間序列評估下，歷史價格、成交量、波動度、少量技術指標與市場情境
特徵，能否預測下一交易日的異常波動／大幅移動風險？

先前「自動中文金融文字訊號能否改善短期方向預測」的問題保留為次要探索研究，不再阻塞主專案完成。

## 三軌定位

- **Track A — Core Research**：`NORMAL`／`HIGH_RISK` 下一交易日波動風險預測。
- **Track B — NLP Intelligence**：英文 FinBERT 與探索性台灣公告／金融 NLP。
- **Track C — Product**：整合風險、市場、新聞、公告及摘要的 Financial Intelligence Assistant。

本系統不是自動交易系統、AI 選股神諭、買賣建議或保證報酬工具。

## 產品版本

- 私人實用版：未來可在受保護的環境保存真實持股與成本，並整合 LINE 推播及券商截圖辨識。
- 受控公開研究版：只使用範例、合成或匿名資料，展示新聞情緒、模型訊號、回測結果與系統架構。

目前狀態：**M1 market dataset complete / next: M2 risk-label protocol / no model training**。

M1 已凍結 10 檔研究 universe、2010 起始的不可變 OHLCV／TAIEX 本機快照，以及
train／validation／sealed-test 時間邊界。品質稽核通過；原始市場資料與 machine report 只留在 Git
忽略路徑，不會隨公開 repository 散布。詳見
[M1 protocol](docs/risk_market_dataset_protocol.md) 與
[raw-free audit summary](research/evaluation/m1_market_dataset_audit.md)。

既有安全基礎、FastAPI、持股、市場／新聞／英文 FinBERT 管線與 feature foundation 均保留。原
M5.5–M9 的中文模型診斷、FSC audit/corpus、BERT/MacBERT pilot、market-reaction engine、weak
supervision 與來源治理已重新定位為 Track B 探索研究；其結果與 sealed-test 邊界均未刪除或改寫。

新里程碑與完成定義見 [PROJECT_PLAN.md](PROJECT_PLAN.md)，舊新里程碑對照見
[research direction migration](docs/research_direction_migration.md)。

## 預計系統架構

目前 FastAPI 提供健康檢查與具 ownership 邊界的持股 API，SQLite 作為本機預設資料庫，
PostgreSQL 為部署目標。Python 負責市場／新聞 ingestion、風險特徵、模型、NLP、時間序列評估
與排程；LINE/GAS adapter 維持在服務邊界。Track A 可在中文 sentiment 維持 unsupported 時獨立
完成；Track B 以情報、metadata、embedding、retrieval 與可選消融提供產品研究價值。

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

## Legacy feature foundation（原 M6）

原 M6 使用交易日 `t` 收盤時已知的資料建立下一交易日方向資料集。它現在是可重用的 legacy
engineering foundation：保留 13:30 cutoff、rolling features、snapshot hash 與 future-price mutation
test；`label_up` 不再是 Track A 的核心 target 或完成門檻。新風險 label 將依新 M2 protocol 另行
版本化。

```bash
alembic upgrade head
financial-ai-features \
  --config research/configs/feature_pipeline.example.json \
  --snapshot artifacts/modeling-dataset.json
```

輸出保存完整設定、`features-v1`、market/sentiment snapshot hash 與 dataset SHA-256。相同輸入重跑會復用既有 dataset run。中文新聞沒有通過歷史 M5.5 採用門檻，因此對應 sentiment probability/score 保持 `null`；新聞數量則為 `0`，不會偽裝成 neutral sentiment。詳細定義見 `docs/feature_definitions.md`。

## Exploratory Track B：台灣金融資料集／語料稽核（原 M6）

事件 taxonomy、impact／ambiguous 規則與先前 AI-to-AI 診斷保留於 `docs/taiwan_financial_annotation_protocol.md`。正式研究路線不使用人工標注或人工覆核；自動訊號、consensus、abstention 與 leakage-safe 評估見 `docs/automated_chinese_text_signal_protocol.md`。候選外部資料只可放在 Git 忽略的 `.tools/` 或 `data/raw/`，不得提交原文。

JSON、JSONL、CSV 可直接稽核；Parquet 另安裝輕量選配依賴：

```bash
python -m pip install -e ".[audit]"
financial-ai-taiwan-dataset-audit --help
```

Eland 只保留為歷史候選資料集的拒絕證據，狀態固定為 **HOLD／排除於主動建模流程**；不得用於訓練、領域自適應、weak supervision、正式評估、特徵或 corpus 合併，也不在本里程碑追加救援或重審。主動來源決策見 `research/evaluation/taiwan_dataset_governance.md`，metadata-first 實查見 `research/evaluation/taiwan_active_source_metadata_audit.md`，Eland 歷史記錄見 `research/evaluation/eland_dataset_preliminary_audit.md`。

已接受的 TWSE metadata 與 FinMind TAIEX benchmark 使用版本化 manifest 執行唯讀 gate：

```bash
financial-ai-source-gate \
  --manifest research/configs/taiwan_active_sources.v1.json \
  --output artifacts/taiwan-source-gate-report.json
```

報告只保存 endpoint、dataset ID、schema、terms URL、時間契約、筆數與 SHA-256，不保存公告原文或價格列；`artifacts/` 已由 Git 忽略。

FSC 官方法規 Open Data 先以 HEAD-only coverage gate 驗證五個 ZIP：

```bash
financial-ai-source-gate \
  --manifest research/configs/fsc_official_sources.v1.json \
  --output artifacts/fsc-official-source-gate-report.json
```

五個 endpoint 均通過，合計宣告大小 7,224,679 bytes。取得使用者批准後，官方 ZIP 已下載至 Git 忽略的 `.tools/datasets/fsc-official/`，並用固定 snapshot 執行不輸出原文的自動稽核：

```bash
financial-ai-fsc-archive-audit \
  --snapshot research/configs/fsc_official_archive_snapshot.v1.json \
  --archive-dir .tools/datasets/fsc-official \
  --output artifacts/fsc-official-archive-audit.json
```

5/5 archive、6,047 筆 XML 紀錄通過結構 gate。決策只接受經自動排除空內容／無法解析發布日、內容 hash 去重與 document-family 隔離後的非商用無標籤 domain-adaptation feasibility；不把官方分類當 sentiment truth，也不批准原文提交、公開重散布或正式模型訓練。完整結果見 `research/evaluation/fsc_official_archive_audit.md`。

M7 corpus 與小型 feasibility：

```bash
python -m research.training.fsc_corpus \
  --config research/configs/fsc_domain_corpus.v1.json \
  --output-dir .tools/corpora/fsc-domain-corpus-v1

python -m research.training.domain_adaptation_feasibility \
  --config research/configs/m7_domain_adaptation_feasibility.v1.json \
  --corpus-dir .tools/corpora/fsc-domain-corpus-v1 \
  --cache-dir .tools/huggingface
```

Corpus 與模型只保存在 `.tools/`；統計報告在被忽略的 `artifacts/`。完整限制與結果見 `research/evaluation/m7_domain_adaptation_feasibility.md`。

批准後的 200-step bounded pilot 已完成，結果見 `research/evaluation/m7_domain_adaptation_pilot.md`。兩候選皆通過至少 1% validation improvement；在相同 vocabulary 下，預先指定的 final MLM loss 規則選出 BERT-base-Chinese 作為下一階段 frozen representation candidate。兩份權重只保存在忽略的 `.tools/models/m7-domain-adaptation-pilot-v1/`。

## Exploratory Track B：自動市場反應 target（原 M8）

M8 以 TWSE 官方事件時間、Yahoo adjusted prices 與 FinMind TAIEX total-return benchmark 建立
next-session／1d／3d raw、benchmark 及 abnormal return。未來價格只存在 target 端；產物、
市場資料與報告都位於 Git 忽略路徑。

```bash
python -m jobs.reaction_labels prepare-market-config
python -m jobs.m8_market_data \
  --config .tools/configs/m8_market_universe.json \
  --start 2026-08-16 --end 2026-08-31
python -m jobs.benchmark_data --start 2026-08-16 --end 2026-08-31
python -m jobs.reaction_labels build
```

首輪結果只驗證工程與 lineage，不能視為 sentiment、因果影響或可訓練資料集；test 的 return
與 reaction-class 統計保持封存。詳細結果見
`research/evaluation/m8_market_reaction_result.md`。

## Exploratory Track B：weak-supervision 核心（原 M9）

M9 已建立最小的版本化 vote 與 aggregation 核心，支援 weighted consensus、coverage、
agreement、vote entropy、`AMBIGUOUS` 與明確 abstention。至少需要兩個獨立自動來源；官方
category 不會被推論 event type 覆寫。現階段只用合成測試，尚未對真實事件執行，也未呼叫
LLM、翻譯服務或外部模型。見 `research/evaluation/m9_weak_supervision_core.md`。

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
