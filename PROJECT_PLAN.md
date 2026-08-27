# Financial AI Assistant — Project Plan

Plan version: `core-direction-migration-v2`
Last revised: 2026-08-27

## 1. 專案名稱與定位

### 英文名稱

**Financial AI Assistant: Stock Volatility Risk Prediction with Financial NLP Intelligence**

### 中文工作名稱

**Financial AI Assistant：股票異常波動風險預警 × 金融 NLP 情報系統**

本專案是一套結合市場資料工程、風險預測、金融 NLP、事件研究與 LINE 互動介面的
**Financial Intelligence Assistant**。

它不是自動交易系統、AI 選股神諭、買賣建議產生器，也不保證獲利或預測準確。

產品維持雙軌：

1. **私人實用版**：在受保護環境保存個人持股、成本與 LINE 推播；私人資料永不進入公開研究資料集。
2. **受控公開研究版**：只使用可公開、範例、合成或匿名資料，展示風險訊號、金融情報、模型評估與系統架構。

本次變更是核心研究方向縮限與里程碑遷移，不是重啟。既有台灣 NLP、來源治理、模型診斷、
FSC、BERT/MacBERT、weak supervision、market reaction、TEJ/TWSE/FinMind 稽核均保留為研究
演進證據。完整對照見 `docs/research_direction_migration.md`。

## 2. 核心研究問題與三軌架構

### 新核心研究問題

> 在嚴格避免資料洩漏的時間序列評估下，歷史價格、成交量、波動度、少量技術指標與市場情境
> 特徵，能否預測下一交易日的異常波動／大幅移動風險？

英文研究問題：

> Can historical price, volume, volatility, technical and market-context features predict
> next-session abnormal volatility / large-move risk under strict leakage-safe temporal evaluation?

原核心問題「自動中文金融文字訊號能否改善價格／成交量／技術特徵的短期方向預測」不再是
專案完成的必要條件，改列 Track B 探索研究與 M10 選配消融。

### Track A — Core Research

**Stock Volatility Risk Prediction**

- 建立可重現的歷史 OHLCV 與市場 benchmark dataset。
- 定義 train-only 的 next-session risk label。
- 建立精簡、可解釋、時間安全的市場特徵。
- 比較 naive、Logistic Regression、Random Forest、HistGradientBoosting／XGBoost。
- 以 chronological validation、walk-forward、sealed test 與 calibration 評估。
- 驗證 HIGH_RISK 與 NORMAL 群組的後續實際波動是否有可重現差異。

Track A 必須能在 Track B 沒有正式中文 sentiment 的情況下獨立完成。

### Track B — NLP Intelligence

**English financial sentiment + Exploratory Taiwan Financial NLP Research**

- 保留 pinned English FinBERT 與既有 pipeline sanity evidence。
- 保留台灣模型拒絕結果、FSC corpus、BERT/MacBERT pilot、frozen representation、weak
  supervision、market reaction、來源治理與 Eland 排除紀錄。
- 台灣公告可提供 entity mapping、官方事件分類、關鍵詞、embedding、相似度、檢索、分群、
  摘要與選配 weak event signal。
- 不支援的中文文本不強迫輸出 Positive／Neutral／Negative，也不偽造機率。
- NLP 是否改善 Track A 只在 timestamp-safe 資料就緒時做 M10 選配實驗；零或負結果必須保留。

### Track C — Product

**Financial Intelligence Assistant**

- FastAPI 提供市場快照、風險訊號、公告／新聞情報、持股與每日摘要 contract。
- Python 負責 ingestion、features、risk model、evaluation、NLP、jobs 與結構化儲存。
- GAS 暫時只作 LINE adapter：路由、backend call、reply／push／Flex UX。
- 產品輸出使用「風險訊號／研究訊號」，不用「買進／賣出」。

## 3. 研究範圍與完成邊界

### Track A MVP

- 市場：台股；先使用資料完整且流動性合理的固定 universe。
- 時點：交易日 `t` 收盤後，以 `t` 及以前可得資訊預測下一個實際交易日 `t+1`。
- 任務：第一版為 `NORMAL`／`HIGH_RISK` 二元分類。
- 頻率：日資料；不做 tick、盤中高頻或跨市場同步交易。
- 模型：可解釋 tabular baseline 加非線性 tree model。
- 目標：預測風險，而不是預測漲跌方向或下達部位指令。

### 非目標

- 不做自動下單或個人化投資建議。
- 不以 Accuracy 單一指標宣稱成功。
- 不因複雜度加入 LSTM／Transformer 價格模型。
- 不以 validation/test 分布選 label threshold。
- 不把 future price、future volatility、future reaction 或 cutoff 後新聞放入特徵。
- 不要求中文情緒通過 gate 才能完成 Track A。

## 4. Track A Risk Label Protocol

新 protocol 建議版本：`next-session-volatility-risk-v1`。M2 實作前必須建立機器可讀設定、
protocol 文件與 leakage tests。

### 4.1 Prediction row

每列代表：`ticker`、`feature_session=t`、`information_cutoff`、下一個實際
`target_session`、`continuous_risk_outcome`、`risk_threshold_version` 與
`risk_label=NORMAL|HIGH_RISK`。

不得把下一個日曆日當成下一交易日。OHLCV `t` 僅能在市場收盤後進入 post-close prediction。

### 4.2 候選可觀測 outcome

候選 outcome 必須先保留為連續值：

1. `next_abs_return`：下一交易日絕對 close-to-close return；
2. `next_high_low_range`：下一交易日 high-low range，例如 `(high-low)/previous_close` 或對數 range；
3. `next_realized_volatility_proxy`：由下一交易日 OHLC 形成、定義固定的 realized-vol proxy；
4. `next_normalized_move`：下一交易日絕對報酬除以 `t` 時已知的 trailing volatility scale。

不得任意混合多個 outcome。M2 需預先指定主要 outcome、次要 robustness outcome 與公式。

### 4.3 Threshold protocol

- 最終 threshold 不得任意硬編碼。
- 候選方法可包含 train percentile、只使用過去資料的 rolling percentile、或 train-fit
  volatility-normalized threshold。
- Validation 可選擇候選 protocol／percentile 與 probability decision threshold；不能重估
  outcome distribution 後回填 test。
- Sealed test 的 label threshold、scaler、imputer、feature selector、probability threshold 與
  calibrator 必須在開 test 前凍結。
- Walk-forward 每個 origin 可只用該 origin 以前的 training history 重估；不可偷看未來 origin。
- 報告必須保存 HIGH_RISK prevalence，避免以極端 threshold 製造不可用少數類別。

### 4.4 Label claims

`HIGH_RISK` 表示依已凍結規則，下一交易日實際波動／大幅移動 outcome 超過風險門檻；它不表示
價格必漲、必跌、事件造成價格變動或應該賣出。

## 5. Track A Feature Groups

特徵以 compact、interpretable、non-redundant 為原則。每個值必須有 availability cutoff、公式、
lookback 與缺值規則。

### Price

- lagged return；
- 1／3／5／10／20-session return；
- overnight gap（資料可靠時）；
- current price relative to moving average／recent range。

### Volume

- lagged volume；
- 1-session volume change；
- rolling mean；
- volume z-score／abnormal volume。

### Volatility

- trailing return standard deviation；
- ATR 或固定公式的 equivalent range feature；
- current high-low range；
- trailing realized-volatility proxy。

### Technical

- RSI；
- MACD；
- moving-average distance；
- momentum。

不得一次加入數十個高度相關技術指標。新增特徵需說明它沒有被現有欄位重複表達。

### Market context

- TAIEX return；
- TAIEX trailing volatility；
- stock-minus-market return；
- market trend／drawdown（有明確公式與研究理由時）。

保留已接受的 FinMind `TaiwanStockTotalReturnIndex`／`TAIEX` 非商用研究 benchmark。若個股 universe
含上櫃標的，必須文件化 benchmark suitability，不得默認所有 OTC 個股與 TAIEX 同質。

## 6. Track A Model Matrix

| 實驗 | 模型 | 目的 |
| --- | --- | --- |
| Baseline 0 | historical-risk rate／persistence naive baseline | 建立最低比較基準 |
| Baseline 1 | Logistic Regression | 主要可解釋 baseline、校準基準 |
| Model 2 | Random Forest | 非線性與交互作用比較 |
| Model 3 | HistGradientBoosting 或 XGBoost | 主要 tabular 候選模型 |

- 模型與超參數選擇只用 train／validation。
- 對不平衡類別使用 class weighting、resampling 或 thresholding 時，所有 fit 只在 train fold。
- 不因模型較複雜就優先採用；主候選需同時考量 HIGH_RISK recall、calibration、穩定性與可解釋性。
- final candidate、feature list、target protocol、preprocessing 與 probability threshold 必須在 sealed
  test 前凍結。

## 7. Temporal and Leakage-Safe Protocol

### 固定切分

```text
TRAIN → VALIDATION → SEALED TEST
```

- 禁止 random train/test split。
- Split 日期、ticker universe、資料 provider 與 snapshot hash 必須版本化。
- Test 在 model／target／feature／threshold／calibration 選定前保持封存；只開一次。
- 若資料修訂導致 snapshot 改變，建立新 dataset version，不覆寫舊 test evidence。

### Walk-forward

- 使用 rolling-origin 或 expanding-window validation。
- 每一 fold 只使用 prediction cutoff 前的資料 fit preprocessing 與模型。
- 若 outcome window 與下一 fold 重疊，加入 purge／embargo。
- 同 ticker 的相鄰資料可能高度相關；信賴區間應考慮時間相依性。

### Train-fit only

Imputer、scaler、feature selection、target threshold、class weights／resampling、probability
threshold、probability calibration 與 model hyperparameters 全部只能在 train 或當下 walk-forward
training window fit。

### Information cutoff

- 每筆 prediction 保存 cutoff 與 target session。
- 價格／成交量／市場／技術 rolling window 結束於 `t`。
- `t+1` high、low、close、volume 只能存在 outcome／label。
- cutoff 後公告或新聞只能進入後續 session。
- future market reaction 僅可作 Track B 離線 target 或過去已完成窗口的統計，不可成為當期特徵。

## 8. Evaluation and Robustness

### 必報分類指標

- Balanced Accuracy；
- Precision；
- Recall；
- F1；
- Macro-F1（適用時）；
- MCC；
- PR-AUC；
- ROC-AUC（兩類均存在且有效時）；
- Brier score；
- calibration curve／reliability table；
- confusion matrix。

必須單獨報告 HIGH_RISK recall、false negatives 與 false-negative rate。Accuracy 只能作補充。

### 分層穩健性

- ticker；
- 時間期間；
- market regime（定義只能使用當時可得市場資料，且樣本足夠）；
- predicted-risk decile／probability bucket；
- HIGH_RISK prevalence 與 calibration drift。

分層樣本不足時必須標示，不可從極小群組做強結論。

### Risk validation

核心驗證不要求自動買賣策略。比較 predicted `HIGH_RISK` 與 predicted `NORMAL` 的下一交易日
absolute return、high-low range、realized-volatility proxy 及適用時的 drawdown。

成功表示風險訊號能分離較高與較低 realized-risk 群組，不表示可獲利。選配 reduced-exposure
backtest 必須晚於核心風險驗證，納入成本，且不可成為 MVP 必要條件。

## 9. Track B — Financial NLP Intelligence

### English FinBERT

- 保留 `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43`。
- 保存 positive／neutral／negative probabilities 與 `positive - negative` score。
- 既有 12-example 約 83.33% 結果只作 pipeline sanity evidence，不是正式 benchmark。
- 中文輸入保持 unsupported，不翻譯、不填 neutral、不偽造 probability。

### Exploratory Taiwan Financial NLP Research

完整保留中文模型診斷與 TWSE 衍生診斷、FSC official-source/archive audit 與 6,021-record
family-isolated corpus、MacBERT／BERT-base-Chinese feasibility 與 200-step pilot、frozen
BERT-base-Chinese representation candidate、zero-manual-label protocol、weak-supervision core、
automatic market-reaction engine、TWSE／FinMind／TEJ source audits 及 Eland 排除紀錄。

這些成果是探索研究與 project evolution evidence，不是 validated Taiwan sentiment truth。不得因新
方向而刪除、改寫失敗結果、打開 sealed NLP test 或啟動新模型訓練。

### Taiwan announcement intelligence

允許用途包括 text normalization、company/entity mapping、official event category、keyphrase、
structured metadata、frozen embeddings、similarity/retrieval/clustering、concise structured
summaries 與 optional weak event signals。無支援時輸出 `unsupported`／`abstain`，不要求三分類。

### Optional NLP ablation contract

只在 timestamp-safe NLP features 不阻塞主線時，以相同期間、target、preprocessing 與 downstream
model 比較 market-only 和 market+NLP。Null／negative 結果仍需保留；Track A 不因 M10 缺資料或無
增益而不完整。

## 10. Track C — Product Architecture

```text
LINE user
  → GAS / LINE adapter (temporary)
  → FastAPI
      ├── market snapshot
      ├── next-session risk prediction
      ├── factor explanation
      ├── news / announcement intelligence
      ├── portfolio service
      └── daily brief
  → structured storage

Scheduled Python jobs
  ├── OHLCV / benchmark ingestion
  ├── risk feature generation
  ├── prediction / monitoring
  ├── news / announcement ingestion
  └── English NLP / Taiwan intelligence
```

GAS 只負責 LINE 事件路由、backend call、reply／push／Flex UX。不得把市場 ingestion、NLP、ML、
回測、多使用者交易或秘密重新放回 GAS。既有可用 GAS 功能本次不修改。Python 是 market/news
ingestion、NLP、features、risk prediction、evaluation、jobs、database 與 storage 的 source of truth。

### UX contract

產品可顯示 ticker、current market snapshot、next-session `NORMAL`／`HIGH_RISK`、risk probability、
top model factors、recent announcements/news、supported English sentiment、Taiwan announcement
intelligence 與 AI Daily Brief。介面只使用 risk/research signal，不使用 buy/sell recommendation。

## 11. Data and Governance

### Market data

- 現有 Yahoo adapter 是研究原型，可替換且需保存 provider／request range／snapshot hash。
- FinMind TAIEX total-return benchmark 目前只接受於非商用研究。
- M1 必須建立足夠 warm-up、train、validation、test coverage 與 exchange-calendar quality audit。
- Potential weekday gaps 不得自動 forward-fill；先以交易日曆驗證。
- Corporate action、provider revision 與 adjusted-price 變更需建立 dataset version。

### News and announcements

- TWSE／TPEx keyless daily OpenAPI 可作 forward official-announcement ingestion。
- TEJ `TWN/AP11` 可被 catalog 搜尋，但目前 trial entitlement 回覆 `PDB003` 無存取權；付費／學術
  授權不是 Track A 完成條件。
- TEJ `特殊事件日期資料庫` 本機匯出是 date-only 結構事件補充，不是重大訊息全文或精確時間。
- TEJ EVENT 可作私人 AR/CAR 交叉驗證；原始 TEJ export 不得在未確認授權前提交或重散布。
- MOPS 歷史 browser 不得逆向、繞過安全控制或假裝成正式 bulk API。

### Restricted/private data

真實 API key、token、LINE ID、Sheet/Doc ID、持股、券商截圖、TEJ raw export 與受限全文不得進
Git。`.env`、`.tools/`、`data/raw/`、`data/private/`、`artifacts/`、imports/uploads/user_data
保持忽略。公開結果只包含合法欄位、統計、hash、設定、模型指標與匿名示例。

## 12. Milestones M0–M15

### M0 — Existing Work Freeze & Plan Migration

- 保存現有 code、documents、artifacts lineage 與負面結果。
- 將舊 milestone 對應至 Track A／B／C。
- 更新 PROJECT_PLAN、HANDOFF、README 與 migration note。
- 不訓練、不開 sealed test、不刪 NLP、不改 GAS。

驗收：新核心問題、三軌、M0–M15 與 Definition of Done 一致；舊證據仍可追溯。

### M1 — Market Dataset

建立固定 universe 的歷史 OHLCV、TAIEX benchmark、exchange-calendar coverage、immutable snapshot
與品質報告；確認 warm-up、train、validation、test 均有足夠資料。相同 input/config 重建 hash
一致，duplicate、missing session、OHLC invariant、volume、corporate action/provider revision 有測試。

**狀態：完成（2026-08-27）。** 已凍結 10 檔 universe、2010-01-01 起始快照、
2011–2022 train、2023–2024 validation 與 2025-01-01–2026-08-26 sealed test。M1 audit 包含
40,691 筆個股列與 4,080 個 TAIEX session，所有缺漏比率低於 3% 且無 fatal issue。資料快照與
machine report 位於 Git 忽略路徑；公開只保留 raw-free 摘要。M1 未產生風險標籤、未訓練模型、
未查看 sealed-test outcome 或績效。下一個單元是 M2 Risk Label Protocol。

### M2 — Risk Label Protocol

版本化 next-session continuous outcomes、train-only threshold estimator、binary label builder 與
mutation leakage tests。改動 `t+1` 只能改 outcome/label，不得改 `t` features；validation/test 不參與
threshold fit。

**狀態：完成（2026-08-27）。** 主要 outcome 為下一交易日絕對 adjusted-close log return 除以
`t` 時可得的 20-session trailing volatility；次要保留 absolute log return、high-low log range 與
Parkinson proxy。候選 threshold 為 25,990 筆 training rows 的 linear 90th percentile
`1.807988011793`，training HIGH_RISK prevalence 為 10%。共 materialize 25,990 train 與 4,800
validation rows；validation distribution 未檢視，sealed-test outcome／label 未生成，且未訓練模型。
Temporal mutation、exact-next-session、cross-split、snapshot hash 與 immutable-output tests 均通過。

### M3 — Feature Pipeline

重用現有 price/volume/technical foundation，新增 10-session return、gap、ATR/range、market
volatility、stock-minus-market 與必要 availability metadata；所有 rolling window 截止於 `t`。

**狀態：完成（2026-08-27）。** `risk-features-v1` 固定 23 個 market-only features：price 7、
volume 3、volatility/range 5、compact technical 3、TAIEX context 5。共 materialize 23,890 train
與 4,800 validation rows，0 null／non-finite；2,100 rows 因 35-session 連續歷史不完整而明確
abstain，未補值或跨缺漏。Stock／TAIEX `t+1` mutation tests 證明同日 feature values/hash 不變。
Validation label distribution 未檢視、sealed-test features 未生成、preprocessing 未 fit、模型未訓練。

### M4 — Baselines

實作 naive historical-risk/persistence baseline 與 Logistic Regression，建立 train-fit preprocessing。
Validation 報告 HIGH_RISK recall、calibration、confusion matrix；test 未開。

### M5 — Tree Models

實作 Random Forest 與 HistGradientBoosting／XGBoost，以同一資料、target、split 公平比較；不以 test
選模型，保存參數、feature importance 與 resource cost。

### M6 — Temporal Validation

執行 chronological validation、walk-forward／rolling-origin、calibration 與 model/threshold selection；
所有 fold preprocessing train-fit only，通過 purge/embargo，凍結 final candidate manifest。

### M7 — Sealed Test

確認 candidate manifest/hash 後只開一次 test，產生 final metrics 與 calibration evidence。Test 不參與
任何選擇，報告包含 HIGH_RISK FN、PR-AUC、MCC、Brier 與 limitations。

### M8 — Risk Error Analysis & Robustness

依 ticker、time、regime、probability bucket 分析，檢查 FN/FP 與 calibration drift；分層樣本數與
不確定性透明，失敗期間不隱藏。

### M9 — Financial NLP Intelligence

維持 English FinBERT，將既有台灣 NLP 定位為 exploratory；實作不依賴 polarity 的公告
normalization、entity/event metadata、embedding/retrieval/summary contract。既有 M5–M9 evidence
全保留，unsupported／abstain 語意明確；不訓練新模型除非另行批准。

### M10 — Optional NLP Incremental-Value Experiment

在 timestamp-safe 資料可用時做 market-only vs market+NLP paired ablation。相同期間、target、model
budget；null/negative 結果保留。**選配且不阻塞。**

### M11 — Risk Backtest / Validation

比較 predicted HIGH_RISK 與 NORMAL 的後續 realized outcomes；可選 reduced-exposure experiment。
主要結果不依賴自動買賣策略；若有 exposure backtest，使用 OOS prediction、成本與非投資建議聲明。

### M12 — Prediction / Intelligence API

提供 risk snapshot、probability、factors、announcements/news、NLP intelligence、model/cutoff version
contract。輸出可追溯至 dataset/model/config hash；LLM 失敗不影響風險結果。

### M13 — LINE Integration & GAS Slimming

GAS 呼叫 backend、保留 Flex UX、逐步移出重複邏輯、最終 webhook signature 驗證。GAS 無 secrets
與重 ML；每位使用者資料隔離；本次 migration 不修改既有 GAS。

### M14 — Public Demo

以範例／匿名資料展示 market snapshot、risk signal、factor explanation、announcements 與 research
limitations。無私人持股、restricted raw data、API key 或 buy/sell 文案。

### M15 — Portfolio Finalization

完成 README、architecture、model comparison、research summary、graduate-application abstract、demo、
limitations、CI/reproducibility evidence。Track A conclusion、Track B boundary、Track C demo 清楚分離。

## 13. Current Evidence Freeze

以下結果不得刪除、重算成不同敘事或因新方向失效：

- M0–M4 安全、FastAPI、持股、market/news pipeline；
- M5 English FinBERT pipeline 與 12-example sanity evidence；
- M5.5 Chinese candidate failed-gate results；
- Taiwan taxonomy、zero-human-label documents 與 AI-to-AI stability diagnostic；
- FSC five-archive audit、6,021-record corpus 與 family-isolated splits；
- MacBERT/BERT feasibility、200-step pilot、frozen BERT-base-Chinese representation decision；
- M8 market-reaction v1 engine 與 all-test bounded snapshot（test distribution 持續封存）；
- M9 weak-supervision minimal aggregation core；
- TWSE／FinMind／TEJ source audits；
- Eland historical HOLD／excluded record。

既有 direction-prediction `features-v1` 與 `label_up` 是 legacy engineering evidence，可重用其市場
features、cutoff alignment、hash 與 mutation tests；它不再定義新 Track A target 或完成條件。

## 14. Security, Privacy and Claims

- 秘密只放 ignored `.env` 或 deployment secret manager。
- LINE webhook 正式環境驗證 signature；ownership check 必須由可信身分 context 建立。
- Logs 不保存 token、完整私人持股、券商影像、restricted text 或含私人資料的 prompt。
- 公開 demo 與私人 portfolio 使用實體分離的 storage/context。
- Perplexity 僅作按需、具來源研究；不作歷史 ground truth 或逐篇 ingestion。
- Gemini OCR 僅可走 preview/confirm schema，不得直接寫入私人持股。
- UI、文件與 prompt 都必須聲明研究用途，不構成投資建議或績效保證。

## 15. Definition of Done

專案完成須同時符合：

1. 可重現的市場 dataset 存在，來源、期間、universe、品質與 snapshot hash 完整。
2. Next-session risk label 使用 train-only 規則，validation/test 未參與 threshold fit。
3. Price/volume/volatility/technical/market features 在 information cutoff 下無 leakage。
4. 至少一個可解釋 baseline 與一個 nonlinear model 完成公平評估。
5. Validation 採 chronological protocol，並有 walk-forward／rolling-origin evidence。
6. Final candidate 在 sealed test 前凍結，test 只開一次。
7. HIGH_RISK recall、false negatives、PR-AUC、MCC 與 calibration 有正式報告。
8. Predicted HIGH_RISK／NORMAL 與後續 realized volatility／large-move outcome 完成比較。
9. NLP 保留為 intelligence layer；中文 sentiment 不再是完成條件。
10. 現有台灣 NLP 研究、失敗結果與 governance 完整保留且不 overclaim。
11. API／LINE／demo 能呈現 risk + intelligence，或至少具備可驗證 contract 與 demo 路徑。
12. 無 secrets、私人持股、券商截圖或 restricted raw dataset 被公開。
13. 無 buy/sell、automatic trading 或 guaranteed-return claim。

中文文字訊號是否改善 Track A **不是** Definition of Done。M10 可以沒有結果、得到 null／negative
結果，或因 timestamp-safe 資料不足而不執行；主專案仍可完成。

## 16. Immediate Execution Boundary

M0 文件遷移與 M1–M3 已完成。禁止打開任何 sealed-test
outcome／performance、刪除
NLP、修改 working GAS、deploy、commit 或 push。

下一個最小可執行單元是 **M4 Baselines**：以 M3 training rows fit 所有 preprocessing，建立
historical-risk／persistence naive baseline 與 Logistic Regression；只在 validation 報告候選指標，
不得產生或打開 sealed test，也不得用 validation fit scaler、imputer、class weight 或模型參數。
