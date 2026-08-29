# Financial AI Assistant

**Stock-Normalized Volatility Surprise Forecasting with Financial NLP Intelligence**

中文研究題目：**基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統**。

這是一套結合市場資料工程、下一交易日相對波動異常預測、金融 NLP 情報、事件研究與 LINE
互動介面的研究型 Financial Intelligence Assistant。

## 核心研究問題

在嚴格避免資料洩漏的時間序列評估下，價格、成交量、波動度與市場情境特徵，能否預測下一交易日
相對於個股自身歷史波動背景的 volatility surprise？

本研究是 **retrospective、leakage-aware、hypothesis-informed final study**。歷史資料已影響問題
形成，因此多段 rolling-origin 結果不會被宣稱為新 sealed test、prospective validation 或 independent
external validation。

## 三軌定位

- **Track A — COMPLETE / FROZEN**：continuous stock-normalized volatility-surprise forecasting；
  final Ridge Regression `alpha=100`。
- **Track B — COMPLETE THROUGH B5**：F8/F10 database-only intelligence 已加入 backward-safe
  Track B contract；metadata magnitude signal 為 `AUTOMATED_SIGNAL_ONLY`，Chinese sentiment 與
  direction 明確 abstain，BERT text 無 incremental value。
- **Track C — Product**：F10/F11A/F11B-D0/1A/1B complete；controlled LINE demo 未部署，
  F11B-2 current-market integration 仍受 gate 阻擋，F12 last。

本系統不是自動交易系統、AI 選股神諭、買賣建議或保證報酬工具。

## 產品版本

- 私人實用版：未來可在受保護的環境保存真實持股與成本，並整合 LINE 推播及券商截圖辨識。
- 受控公開研究版：只使用範例、合成或匿名資料，展示新聞情緒、模型訊號、回測結果與系統架構。

目前狀態：**F11B-1B controlled read-only demo complete / not deployed / F11B-2 gated**。

- 中文 sentiment 目前仍為 `ABSTAIN / CHINESE_SENTIMENT_NOT_VALIDATED`。
- AP11 是 optional enhancement，不是 Chinese NLP、F11B 或 F12 的前置條件。
- eLAND 永久排除於 active work，只保留歷史拒絕證據。
- GAS 後續只可在 verified private migration copy 上依 rollback 規則演進；R0 未改 live behavior。
- B2 v1 frozen whitelist 為 FSC filtered corpus、TWSE/TPEx daily official announcements 與 GDELT
  metadata；FinMind remains conditional。TWMD 經後續 Pro 小樣本稽核升為 `ACCEPT_SECONDARY`
  （只限 major-event taxonomy／issuer mapping）；B2.1 fail-closed contract/provider 已完成，但
  尚無 TWMD dataset rows，未加入 B2 v1 或 B3；eLAND 仍永久排除。詳見
  [B1 source candidate audit](research/evaluation/b1_source_candidate_audit.md)。
- B2 已建立 6,021 筆 private normalized FSC snapshot、TPEx forward provider 與 TWSE/TPEx/GDELT
  長期 acquisition/reconciliation contract；無最低等待期，也未部署 collector。詳見
  [B2 acquisition contract](docs/b2_data_acquisition_and_update_contract.md) 與
  [B2 result](research/evaluation/b2_taiwan_financial_text_dataset_result.md)。
- B3 重用並驗證既有 200-step FSC MLM pilot，promote 單一 BERT-base-Chinese representation
  candidate；沒有 sentiment fine-tuning、pseudo-label training 或人工標注。中文 sentiment
  仍 `ABSTAIN`。詳見 [B3 protocol](docs/b3_domain_and_candidate_signals_protocol.md) 與
  [B3 result](research/evaluation/b3_domain_and_candidate_signals_result.md)。
- B3.1 只稽核 CFSC-ABSA、multilingual Chinese financial sentiment 與 StockSentCN。三者目前
  均為 `HOLD`：分別受標註／授權／aspect split、標註來源與授權衝突、以及 weak/pseudo label
  與不可取得 gold subset 限制；gate answer 為 `NO`，未建立 B3.2 或訓練模型。詳見
  [B3.1 audit](research/evaluation/b3_1_chinese_sentiment_label_source_audit.md)。
- B4 將 linguistic sentiment 與 market reaction 明確分離，凍結 publication-time 對齊、
  TAIEX abnormal-return target、dedup 與 chronological gates。更正早期 `limit=2` probe 誤用
  後，2021–2025 TWMD 私有回填取得 7,582 events、3,433 windows、9 tickers；metadata-only
  對 absolute reaction 有 modest ranking signal，但 BERT title text 未增加效益。市場反應模型
  為 `AUTOMATED_SIGNAL_ONLY`，中文 sentiment 仍為獨立 abstain。詳見
  [B4 protocol](docs/b4_market_reaction_validation_protocol.md) 與
  [B4 result](research/evaluation/b4_market_reaction_validation_result.md)。
- B5 沿用 F8/F10 architecture，在既有 intelligence item 加入 optional/backward-safe
  `track_b_intelligence`：event class、Chinese abstention、stored B4 magnitude band、media-tone
  proxy status、BERT representation lineage 與限制完全分離；API request 不呼叫 provider、模型
  或 LLM。詳見 [B5 protocol](docs/b5_nlp_intelligence_integration_protocol.md) 與
  [B5 result](research/evaluation/b5_nlp_intelligence_integration_result.md)。
- F11B-D0 已凍結六入口 LINE menu、股票分析／持股健檢／金融情報 Flex、多使用者角色與
  資料隔離、LINE signature/auth trust boundary、GAS/FastAPI ownership、legacy preservation、
  controlled demo 與 current-market gate。只建立設計文件/config/tests，未修改 GAS 或部署。
  詳見 [F11B-D0 design](docs/f11b_line_product_design_freeze.md)。
- F11B-1A 已在 private migration copy 建立六入口 parser/dispatcher 並保持 legacy flow；
  F11B-1B 新增 HMAC-authenticated FastAPI static-fixture endpoint 與受控 Flex renderer，只接受
  合成 2330 fixture，零 provider/model/portfolio access，未部署。詳見
  [F11B-1B controlled demo](docs/f11b_controlled_line_demo.md)。

單一正式 roadmap 與 Definition of Done 見
[R0 project rebaseline protocol](docs/r0_project_rebaseline_protocol.md)，GAS 安全凍結見
[GAS migration safety freeze](docs/gas_migration_safety_freeze.md)。

## 研究演進

本專案最初把 normalized continuous outcome 轉為 `HIGH_RISK`／`NORMAL`，完成嚴格 temporal
evaluation、一次 M7 sealed binary evaluation、robustness、conditional analysis 與 threshold studies。
這些研究不是失敗，也沒有被刪除。

探索性 binary formulation 揭露明顯的 threshold／regime sensitivity。M9 顯示，比起 unconditional
absolute volatility，更穩定的訊號是 stock-relative volatility surprise；M11 雖改善跨 regime operating
stability，卻沒有提升 general discrimination。因此最終研究改為直接預測連續 normalized surprise，
以 regression、Spearman、decile ranking 與 lift 為主。

以下 M1–M11 是完整保留的 **Exploratory Research History**，同時提供 F2/F3 可重用的 data/feature
engineering foundation。

M1 已凍結 10 檔研究 universe、2010 起始的不可變 OHLCV／TAIEX 本機快照，以及
train／validation／sealed-test 時間邊界。品質稽核通過；原始市場資料與 machine report 只留在 Git
忽略路徑，不會隨公開 repository 散布。詳見
[M1 protocol](docs/risk_market_dataset_protocol.md) 與
[raw-free audit summary](research/evaluation/m1_market_dataset_audit.md)。

M2 已建立 next-session normalized volatility-risk outcome、train-only 90th-percentile candidate
threshold 與 `NORMAL/HIGH_RISK` label。只 materialize train／validation；sealed test outcome／label
尚未生成。詳見 [M2 protocol](docs/risk_label_protocol.md) 與
[M2 raw-free audit](research/evaluation/m2_risk_label_audit.md)。

M3 已建立 23 個固定、可解釋、只使用 `t` 資訊的 price／volume／volatility／technical／TAIEX
features，共 23,890 train 與 4,800 validation rows，0 null；sealed-test features 尚未生成。詳見
[M3 protocol](docs/risk_feature_protocol.md) 與
[M3 raw-free audit](research/evaluation/m3_risk_feature_audit.md)。

M4 已用 training-only `StandardScaler` 建立 historical-risk、previous-period persistence 與
class-balanced Logistic Regression 基線，並只在 validation 評估。Logistic Regression 的
HIGH_RISK recall 為 0.582、PR-AUC 為 0.172、ROC-AUC 為 0.645；這是候選基線結果，不代表已選定
final model，且 sealed test 完全未開啟。詳見 [M4 protocol](docs/risk_baseline_protocol.md) 與
[M4 raw-free result](research/evaluation/m4_risk_baseline_result.md)。

M5 已在相同資料、target、split 與固定 threshold 下評估 Random Forest 與
HistGradientBoosting。兩個 tree model 都未超過 M4 Logistic Regression 的 HIGH_RISK recall、
PR-AUC 或 ROC-AUC；此負面比較結果完整保留，尚未選定 final model。詳見
[M5 protocol](docs/risk_tree_model_protocol.md) 與
[M5 raw-free result](research/evaluation/m5_risk_tree_model_result.md)。

M6 已完成 2017–2024 五段 expanding-window validation。依預先規則選出 Logistic Regression、
prequential Platt calibration 與 threshold 0.10，並以 2011–2024 全部 28,690 個 pre-test rows
凍結 candidate manifest。這仍只是待測候選；sealed test evaluation count 為 0。詳見
[M6 protocol](docs/risk_temporal_validation_protocol.md) 與
[M6 raw-free result](research/evaluation/m6_risk_temporal_validation_result.md)。

M7 已依 frozen manifest 唯一一次開啟 2025-01-01–2026-08-26 sealed test。3,647 個 eligible rows
的 HIGH_RISK recall 為 0.508、PR-AUC 0.189、ROC-AUC 0.686、MCC 0.155、Brier 0.0926。
Predicted HIGH_RISK 的 normalized outcome 較高，但 raw absolute return／range 未同步較高，顯示
模型預測的是相對波動異常而非絕對價格振幅；此限制不隱藏。Evaluation counter 已固定為 1，禁止
重跑或依 test 改模型。詳見 [M7 protocol](docs/risk_sealed_test_protocol.md) 與
[M7 final result](research/evaluation/m7_risk_sealed_test_result.md)。

M8 已只讀既有 M7 immutable evaluation，完成 ticker、quarter、pre-test-fit volatility regime、
probability bucket、FN／FP 與 1,000 次 feature-session cluster bootstrap 分析。Recall 的 95% 區間為
0.441–0.576，MCC 為 0.109–0.202；但 2026-Q2 recall 僅 0.310，且不同股票與 regime 的
sensitivity／specificity 差異明顯。Normalized risk separation 持續存在，raw outcome 則高度依賴
conditioning，不能宣稱一般絕對波動預測。詳見 [M8 protocol](docs/risk_robustness_protocol.md) 與
[M8 result](research/evaluation/m8_risk_robustness_result.md)。

M9 進一步確認 composition reversal：三個 raw volatility outcomes 在 aggregate 為負差，但在每個
stock-volatility regime 內皆為正，共同 regime 權重標準化後也轉正。這支持描述性的 Simpson-type
composition effect 與 **stock-normalized volatility surprise risk** 定位；ticker raw directions 仍混合，
因此不能宣稱一般 absolute-volatility predictor。詳見
[M9 result](research/evaluation/m9_conditional_risk_result.md)。

M10 只重建 M6 development OOF evidence，選出尚未經新 holdout 驗證的 Screening 0.09、Balanced
0.11 與 Precision 0.13 candidates。它們呈現 recall／false-alarm trade-off，但 Precision candidate
precision 仍僅 0.193，因此目前不能作 high-confidence UX。歷史 0.10 未被取代；詳見
[M10 result](research/evaluation/m10_operating_point_result.md)。

M11 使用相同 13,550 筆 development OOF evidence 與每折 earlier-history volatility tertiles，在
125,000 組門檻中選出 LOW 0.12／MIDDLE 0.10／HIGH 0.08。相較全域 0.10，跨 regime recall range
由 0.405 降至 0.034、specificity range 由 0.426 降至 0.043，但 MCC 由 0.139 降至 0.131；這是
穩定性候選，不是全面性能提升。它尚未經 M12 新 holdout 驗證，不能產品化。詳見
[M11 result](research/evaluation/m11_regime_threshold_result.md)。

## Active Final Study

F1 已凍結 primary target：下一交易日絕對 adjusted-close log return，除以 `t` 時已知、截至 `t`
的 20-session population volatility。`sigma20 <= 1e-8` 或 non-finite row 明確 abstain；`t+1` 僅在
target 端。模型只包含 normalized-move persistence、Ridge 與 HistGradientBoostingRegressor。

歷史評估使用 2017–2018、2019–2020、2021–2022、2023、2024、2025、2026 partial 七個 expanding
outer folds，每折 hyperparameters 只由 outer training history 內最近三個完整年度 inner folds 選擇。
必報 MAE、RMSE、R²、Spearman、top-decile/quintile lift、deciles 與 ticker/time/regime robustness。

完整 frozen protocol 見
[final study protocol](docs/final_volatility_surprise_study_protocol.md)，舊 M→新 F 對照見
[final study migration](docs/final_study_migration.md)。F2 已從 38,290 candidate rows 建立 32,357
eligible rows，dataset SHA-256 為
`2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`；完整 coverage/exclusion
結果見 [F2 report](research/evaluation/f2_historical_dataset_result.md)。

F3 已驗證全部 32,357 rows 的 exact-next-session、target 重算、23-feature availability、lineage 與
hash。Coverage-bias audit 顯示 ticker 與已知 volatility regimes 沒有異常集中，但
2012/2013/2016/2017/2019 與 2017–2018 outer fold 有時間集中，因此正確狀態是「有時間集中現象的
資料限制」，不能宣稱 exclusions 無偏。詳見
[F3 audit](research/evaluation/f3_target_feature_coverage_audit_result.md)。

F4 已實作 normalized persistence、4 個 Ridge alpha 與 16 個 HGB parameter combinations。Ridge
scaler 僅能 fit training rows，HGB 關閉 internal early stopping；合成資料重建 manifest 與 predictions
均 deterministic。詳見
[F4 result](research/evaluation/f4_regression_candidates_result.md)。

F5 已依 frozen nested temporal protocol 跑完七個 historical outer folds，共 20,637 個 evaluation
rows 與 61,911 個三模型 OOF predictions。Mean outer Spearman 為 persistence 0.0608、Ridge
0.1940、HGB 0.1863；Ridge/HGB 落在 0.01 practical-tie boundary 內。兩者平均 R² 皆接近零且略負，
因此現階段證據較支持 modest ranking signal，不支持精準 magnitude prediction。F5 沒有選 winner
或建立 final artifact；詳見 [F5 result](research/evaluation/f5_nested_temporal_evaluation_result.md)。

F6 已使用 immutable F5 OOF 完成 decile、top-decile/quintile lift、ticker/time/regime robustness
與 1,000 次 feature-session cluster bootstrap。Ridge/HGB mean top-decile lift 分別為 1.354/1.361，
pooled outer-assigned deciles 皆為 9/9 上升，且兩者在所有 outer periods、tickers 與 regimes 的
ranking 都為正；但個別年度只有 5–9 個 monotonic steps，bootstrap intervals 亦重疊。F6 未重新
調參或選 final model；詳見 [F6 result](research/evaluation/f6_ranking_robustness_result.md)。

F7 已依 frozen selection rule 正式選定 Ridge：Ridge/HGB 為 practical tie，再由較低 mean outer
MAE 決勝；2023–2025 temporal validation 選出 alpha 100。最終 fit 使用全部 32,357 eligible rows，
並建立包含 scaler、coefficients、20,637 筆 OOF percentile reference 與 LOW/MODERATE/HIGH/
VERY HIGH band policy 的 safe JSON artifact。模型尚未部署，也不宣稱 prospective accuracy；詳見
[F7 result](research/evaluation/f7_final_research_model_result.md)。

F8 已將 pinned English FinBERT、language gate、ticker matching、TWSE 官方 metadata 與台灣
deterministic event cues 統一為 abstention-safe intelligence contract。英文未執行 optional model
時不生成分數；中文 sentiment 一律 abstain 且 probabilities 為 null；event/impact proxy 另列且不是
sentiment ground truth。F8 驗證 7/7 歷史證據 hash，未下載/推論/訓練模型、呼叫 API/LLM 或部署。
詳見 [F8 result](research/evaluation/f8_financial_nlp_intelligence_result.md)。

F10 已提供 versioned research API：`POST /api/v1/research/volatility-surprise/predict` 驗證完整
23-feature contract 後回傳 score、historical percentile、band 與 lineage；
`GET /api/v1/research/intelligence/{ticker}` 只讀已入庫新聞、ticker 關聯及既有 pinned English
FinBERT 結果，中文仍 abstain。API 不即時抓新聞、執行 NLP/LLM 或回傳私人持股；尚未部署。
詳見 [F10 result](research/evaluation/f10_backend_integration_result.md)。

F11A 已建立 Streamlit Dashboard，預設讀取固定合成 fixture 且完全離線；也可選擇連接同一台
電腦上的 F10 API。畫面呈現 continuous score、historical percentile、communication band、合成
市場情境、中文 abstention 與英文 eligible-not-scored 情報。這不是即時 2330 資料、模型績效或
投資訊號；F11A 沒有修改 LINE/GAS、呼叫外部 provider 或部署。詳見
[F11 result](research/evaluation/f11_dashboard_demo_result.md)。

F11B LINE/GAS integration 尚未開始。R0 已建立 private immutable backup 與 migration copy，未改
live GAS。未來先加入唯讀、受控的 `risk`／`intel` routing；既有持股寫入、Sheet schema、券商截圖
與排程不在第一階段修改。即時風險必須等 audited current market source 與 exact 23-feature parity
驗證後才可啟用。

既有安全基礎、FastAPI、持股、市場／新聞／英文 FinBERT 管線與 feature foundation 均保留。原
M5.5–M9 的中文模型診斷、FSC audit/corpus、BERT/MacBERT pilot、market-reaction engine、weak
supervision 與來源治理已重新定位為 Track B 探索研究；其結果與 sealed-test 邊界均未刪除或改寫。

新里程碑與完成定義見 [PROJECT_PLAN.md](PROJECT_PLAN.md)，舊新里程碑對照見
[research direction migration](docs/research_direction_migration.md)。

## 預計系統架構

目前 FastAPI 提供健康檢查與具 ownership 邊界的持股 API，SQLite 作為本機預設資料庫，
PostgreSQL 為部署目標。Python 負責市場／新聞 ingestion、volatility-surprise features、模型、NLP、時間序列評估
與排程；LINE/GAS adapter 維持在服務邊界。Track A 已在中文 sentiment 維持 unsupported 時獨立
完成並凍結；Track B 依 B1–B5 建立台灣金融文字能力，並以情報、metadata、embedding、retrieval
與可選 B6/F9 消融提供產品研究價值。

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

## 啟動受控 Dashboard

```bash
python -m pip install -e ".[dev,demo]"
streamlit run demo/app.py
```

預設「受控離線示範」不會發出網路請求；「本機 FastAPI」模式只允許 loopback origin。完整
使用與安全邊界見 [demo/README.md](demo/README.md)。

## M2 持股 API

第一迭代提供：

- `GET /users/{user_id}/portfolio`
- `POST /users/{user_id}/holdings`
- `PATCH /users/{user_id}/holdings/{holding_id}`
- `POST /users/{user_id}/portfolio-sync/preview`
- `POST /users/{user_id}/portfolio-sync/{operation_id}/confirm`

過渡期 API 要求 `X-User-ID` 與路徑中的 `user_id` 相同，以測試 ownership 隔離。這不是公開環境的最終身份驗證；F11B 必須改由具服務驗證、replay protection 與可靠 LINE identity mapping 的 backend boundary 提供 user context。

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

以下是歷史英文人工樣本 error-analysis CLI，僅保留為既有工具記錄；**不屬於目前 B1–B6
zero-manual-label/review 路線，請勿在 active Track B 建立或覆核人工標籤**：

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
test；`label_up` 不再是 Track A 的核心 target 或完成門檻。F1 已將新的連續 target 版本化，且不再
建立 `HIGH_RISK`／`NORMAL` 訓練標籤。

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
