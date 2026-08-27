# Financial AI Assistant — Project Plan

Plan version: `post-m8-risk-extension-v3`
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
專案完成的必要條件，改列 Track B 探索研究與 M15 選配消融。

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
- NLP 是否改善 Track A 只在 timestamp-safe 資料就緒時做 M15 選配實驗；零或負結果必須保留。

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

## 8A. Post-M8 Risk Research Extensions

M7 與 M8 是 immutable historical evidence。M7 只有一份 3,647-row evaluation，歷史 operating
threshold 固定為 0.10；M8 只讀該 evaluation 並揭露 regime、ticker 與 period 異質性。兩者不得
再用於 model／calibrator／threshold selection，也不得把 M8 subgroup 結果當 validation data。

### Motivation from M8

M8 顯示 aggregate predicted HIGH_RISK 的 normalized outcome 較高，但 aggregate raw absolute
return、range 與 Parkinson proxy 較低；依 stock-volatility regime 分層後，三個 raw comparisons
卻都轉為正值。這可能是 composition／Simpson-type effect，但不是已證明的因果悖論。固定 0.10
同時呈現 screening 性質：recall 0.508、precision 0.180，且 LOW/HIGH stock-volatility regimes 的
recall／specificity 分別為 0.811/0.377 與 0.383/0.822。

### Extension research questions

- **RQ-A — Conditional interpretation：**模型主要辨識 absolute future volatility，還是相對個股
  自身歷史 regime 異常的 volatility surprise？
- **RQ-B — Operating-point calibration：**只用 pre-test development evidence，能否建立適合不同
  產品用途的 precision／recall operating points？
- **RQ-C — Regime-aware policy：**one frozen model + regime-aware thresholds 能否降低跨 regime
  sensitivity／specificity instability？
- **RQ-D — Model complexity：**只有 threshold policy 仍不足時，regime-specific modeling 的增益
  是否足以抵銷複雜度與過度擬合風險？

執行順序固定為 M9 conditional analysis → M10 development operating points → M11 regime-aware
thresholds → M12 new untouched holdout → 選配 M13 regime-specific modeling。M13 不得自動開始。
完整方法與機器規格見 `docs/post_m8_risk_research_extension_protocol.md` 及
`research/configs/post_m8_*.v1.json`。

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
model 比較 market-only 和 market+NLP。Null／negative 結果仍需保留；Track A 不因 M15 缺資料或無
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

## 12. Milestones M0–M20

### M0 — Existing Work Freeze & Plan Migration

- 保存現有 code、documents、artifacts lineage 與負面結果。
- 將舊 milestone 對應至 Track A／B／C。
- 更新 PROJECT_PLAN、HANDOFF、README 與 migration note。
- 不訓練、不開 sealed test、不刪 NLP、不改 GAS。

驗收：新核心問題、三軌、M0–M20 與 Definition of Done 一致；舊證據仍可追溯。

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

**狀態：完成（2026-08-27）。** 以 23,890 training rows 單獨 fit `StandardScaler`、balanced class
weights 與 Logistic Regression，固定 decision threshold 0.5，不做 imputation、resampling、
hyperparameter／threshold selection。Historical-risk、previous-period persistence 與 Logistic
Regression 均在 4,800 validation rows 評估；validation 不參與 fit。Logistic baseline 的
HIGH_RISK recall 0.582、PR-AUC 0.172、ROC-AUC 0.645、MCC 0.122、Brier 0.224；結果只作基線，
不宣告 final candidate。Sealed test 未 materialize 或開啟。

### M5 — Tree Models

實作 Random Forest 與 HistGradientBoosting／XGBoost，以同一資料、target、split 公平比較；不以 test
選模型，保存參數、feature importance 與 resource cost。

**狀態：完成（2026-08-27）。** Random Forest 與 HistGradientBoosting 使用同一組 23,890 train／
4,800 validation rows、23 features、binary target 與固定 threshold 0.5；參數預先固定，未搜尋、
未 resample、未用 validation early stopping。Random Forest 的 recall／PR-AUC／ROC-AUC 為
0.307／0.156／0.613，HGB 為 0.338／0.151／0.614，均未超過 M4 Logistic 的
0.582／0.172／0.645。此負面結果保留，未選 final model。兩模型的 validation permutation
importance 都以 `volatility_log_return_20` 為首；resource cost 與完整 lineage 已保存。第一次
parallel Random Forest 重跑出現 prediction hash 細微不一致，診斷產物保留後改為 single-thread，
連續兩次 immutable rebuild 通過。Sealed test 未開。

### M6 — Temporal Validation

執行 chronological validation、walk-forward／rolling-origin、calibration 與 model/threshold selection；
所有 fold preprocessing train-fit only，通過 purge/embargo，凍結 final candidate manifest。

**狀態：完成（2026-08-27）。** 五個 expanding-window folds 覆蓋 2017–2018、2019–2020、
2021–2022、2023、2024；每 fold training target 必須在 evaluation 開始前完成，無 outcome overlap。
Logistic 的 mean-fold PR-AUC 0.180，高於 Random Forest 0.170 與 HGB 0.167，依預先規則入選。
Prequential Platt 只用先前 folds 的 OOF probability／label fit，pooled Brier 由 0.224 降至 0.089；
因校準後 0.5 threshold 不適用，再依「recall ≥ 0.50 時最大 MCC」選出 0.10，pooled recall
0.586、MCC 0.139、PR-AUC 0.184。最終 recipe 以 28,690 個 2011–2024 pre-test rows fit 並凍結，
candidate manifest SHA-256 為
`951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`；連續兩次 immutable
重跑通過。Sealed-test evaluation count 為 0。

### M7 — Sealed Test

確認 candidate manifest/hash 後只開一次 test，產生 final metrics 與 calibration evidence。Test 不參與
任何選擇，報告包含 HIGH_RISK FN、PR-AUC、MCC、Brier 與 limitations。

**狀態：完成（2026-08-27；evaluation sequence 1，禁止重跑）。** 使用者明確批准後，系統先建立
immutable opening intent，再以 frozen Logistic／Platt／0.10 recipe 評估 2025-01-01–2026-08-26。
共 3,647 eligible rows、390 個 HIGH_RISK；recall 0.508、precision 0.180、PR-AUC 0.189、
ROC-AUC 0.686、MCC 0.155、Balanced Accuracy 0.615、Brier 0.0926，FN 192。Predicted
HIGH_RISK 的 normalized outcome mean／median 為 1.087／0.876，高於 predicted NORMAL 的
0.766／0.574；但 raw absolute return 與 high-low range 反而較低，因此只能主張 moderate
normalized-risk separation，不能主張 general absolute-volatility、方向或投資效益。Opening、
evaluation、completion 三個 hashes 已保存，model/threshold selection performed=false。

### M8 — Risk Error Analysis & Robustness

依 ticker、time、regime、probability bucket 分析，檢查 FN/FP 與 calibration drift；分層樣本數與
不確定性透明，失敗期間不隱藏。

**狀態：完成（2026-08-27）。** M8 只讀唯一一份 M7 immutable evaluation，先驗證
candidate/opening/evaluation/completion/report hash chain 與 evaluation sequence 1，再以 pre-test-only
tertiles 建立 stock／market volatility regimes。完成 10 ticker、7 quarter、fixed probability bins、
FN／FP 與 normalized/raw realized outcomes 分析；1,000 次 feature-session cluster bootstrap 的 recall
95% interval 為 0.441–0.576、MCC 為 0.109–0.202。季度與 ticker 異質性及 raw outcome 的
conditioning dependence 均已揭露；沒有重跑 M7、重新 fit、改 threshold 或 test-based selection。

### M9 — Conditional Risk / Simpson Analysis

**狀態：protocol frozen，尚未執行。** 只讀既有 M7 predictions；不 refit、不改 prediction、不改
0.10 threshold。比較 aggregate、pre-test-fit stock-volatility regime、ticker 與 quarter 的 raw／
normalized outcomes，並量化 predicted groups 的 regime／ticker／period composition。選配透明的
OLS/HC3 conditional diagnostic，不回饋 classifier。結論必須分開 aggregate absolute-volatility、
within-regime 與 normalized surprise evidence，只能在統計結構支持時稱 Simpson-type effect。

### M10 — Operating-Point Calibration Study

**狀態：protocol frozen，threshold search 尚未執行。** 只使用 M6 2017–2024 walk-forward OOF
development evidence 的 deterministic reconstruction；M7/M8 labels 禁止進入。預先凍結
0.01–0.50 grid、Screening／Balanced／Precision objectives、constraints 與 tie-breakers。所有輸出
仍是 development-only，不回溯取代歷史 0.10。

### M11 — Regime-Aware Threshold Study

**狀態：protocol frozen，threshold search 尚未執行。** 優先測試 one frozen model + LOW/MIDDLE/HIGH
thresholds，不建立 separate models。Regime 由 `t` 已知的 trailing 20-session volatility 定義；每個
development fold cutoff 只 fit earlier training history。以降低跨 regime recall／specificity dispersion
為主要目的，並與 0.10 及 M10 global policies 比較。

### M12 — Prospective / New-Holdout Validation

**狀態：protocol frozen，holdout 尚不可得且未開啟。** 從 2026-08-26 後第一個交易日起 prospectively
收集；opening 前先以 immutable manifest 凍結 model、features、label、三類 policies、regimes 與
metrics。三類 policy 必須在同一 holdout 評估，subgroup 結果不得再調參；樣本不足時只稱
prospective exploratory validation。

### M13 — Optional Regime-Specific Modeling

**選配；不得自動開始。** 只有 M11/M12 顯示 threshold policy 仍不足且有明確 incremental evidence，
並經使用者另行批准後，才評估 separate classifiers、regime interactions 或 mixture-of-experts。
必須先提出 sample-size、overfitting、transition stability、multiplicity、deployment 與 explainability
的 complexity justification。

### M14 — Financial NLP Intelligence

維持 English FinBERT，將既有台灣 NLP 定位為 exploratory；實作不依賴 polarity 的公告
normalization、entity/event metadata、embedding/retrieval/summary contract。既有 legacy M5–M9
evidence 全保留，unsupported／abstain 語意明確；不訓練新模型除非另行批准。

### M15 — Optional NLP Incremental-Value Experiment

在 timestamp-safe 資料可用時做 market-only vs market+NLP paired ablation。相同期間、target、model
budget；null/negative 結果保留。**選配且不阻塞。**

### M16 — Risk Backtest / Validation

比較 predicted HIGH_RISK 與 NORMAL 的後續 realized outcomes；可選 reduced-exposure experiment。
主要結果不依賴自動買賣策略；若有 exposure backtest，使用 OOS prediction、成本與非投資建議聲明。

### M17 — Prediction / Intelligence API

提供 risk snapshot、probability、factors、announcements/news、NLP intelligence、model/cutoff version
contract。未經 M12 驗證前只暴露歷史 0.10 research configuration，不提供多 operating modes。

### M18 — LINE Integration & GAS Slimming

GAS 呼叫 backend、保留 Flex UX、逐步移出重複邏輯、最終 webhook signature 驗證。GAS 無 secrets
與重 ML；每位使用者資料隔離；本次 migration 不修改既有 GAS。

### M19 — Public Demo

以範例／匿名資料展示 market snapshot、risk signal、factor explanation、announcements 與 research
limitations。無私人持股、restricted raw data、API key 或 buy/sell 文案；M12 前不顯示未驗證 modes。

### M20 — Portfolio Finalization

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

中文文字訊號是否改善 Track A **不是** Definition of Done。M15 可以沒有結果、得到 null／negative
結果，或因 timestamp-safe 資料不足而不執行；主專案仍可完成。

## 16. Immediate Execution Boundary

M0 文件遷移與 M1–M8 已完成。Sealed test 已評估一次，永久禁止重跑、重開或依 test 改參數。
後續里程碑不得重新產生 sealed-test outcome／performance、刪除既有 NLP 證據、修改 working
GAS、deploy、commit 或 push，除非使用者另行明確授權。

本次只完成 post-M8 protocol/config migration，尚未執行 M9–M12。下一個最小可執行單元是
**M9 Conditional Risk / Simpson Analysis**：只能讀既有 M7 immutable predictions 做 diagnostic，
不得 refit、改 prediction、改 0.10 threshold 或回饋 classifier。M10/M11 只能使用 2024-12-31
以前的 development evidence；M12 holdout 仍不可得且未開啟。不得呼叫 M7 job、修改 working GAS、
deploy、commit 或 push。
