# Financial AI Assistant — Final Project Plan

Plan version: `final-volatility-surprise-study-v1`

Last revised: 2026-08-28
Active milestone: **F11 complete; optional F9 not run; next review unit is F12**

## 1. Final Project Identity

### English research title

**Stock-Normalized Volatility Surprise Forecasting with Financial NLP Intelligence**

### 中文研究題目

**基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統**

### Product name

**Financial AI Assistant**

本專案結合台股市場資料工程、連續相對波動異常預測、金融 NLP 情報、FastAPI 與 LINE/GAS
互動介面。它不是自動交易系統、價格方向預言、買賣建議或報酬保證工具。

產品維持兩種部署邊界：

1. **私人實用版：**受保護環境中的個人持股、成本與 LINE 推播；私人資料不進入公開研究。
2. **受控公開研究版：**只使用合法、範例、合成或匿名資料，展示模型、排名、情報與架構。

## 2. Research Refinement, Not Research Failure

原 Track A 將連續 normalized-risk outcome 轉為 `HIGH_RISK`／`NORMAL`，再研究 classifier
probability、calibration 與 decision threshold。M7–M11 顯示：

- binary performance 對 threshold 高度敏感；
- precision／recall trade-off 明顯；
- operating behavior 隨歷史個股波動 regime 改變；
- regime-aware thresholds 可大幅降低跨 regime instability，卻沒有同步改善 general
  discrimination；
- M9 的 aggregate raw absolute-volatility 結果在 conditioning 後反轉；
- stock-normalized／relative volatility-surprise outcome 比 unconditional absolute-volatility
  解釋更一致。

因此最終研究不再把自然連續的訊號強制壓成二元 target。標準敘事為：

> The exploratory binary-risk formulation revealed substantial threshold and regime sensitivity.
> Conditional analysis showed that the more stable signal was stock-relative volatility surprise
> rather than unconditional absolute volatility. The final study therefore reformulates the task
> as continuous stock-normalized volatility-surprise forecasting.

這是由探索證據產生的 research-question refinement，不是否定或刪除先前工作。

## 3. Research Integrity and Claim Boundary

最終研究的正確定位是：

**RETROSPECTIVE, LEAKAGE-AWARE, HYPOTHESIS-INFORMED FINAL STUDY**

既有歷史資料已影響問題定義，因此不得把完整歷史評估稱為：

- pristine untouched final test；
- prospective validation；
- independent external validation；
- preregistered confirmation。

2017–2026 的多段歷史資料可作 chronological outer evaluation periods／retrospective
out-of-sample folds。2025–2026 雖可在 rolling-origin 中使用，但已在 binary exploratory study
被檢視，不能重新封裝成新 sealed test。自然累積的未來資料只列為 **Future External Validation**，
不阻塞本專案完成。

## 4. Final Research Questions

### Primary RQ

> Can leakage-safe price, volume, volatility and market-context features forecast next-session
> volatility surprise relative to each stock's own historical volatility context?

### Secondary RQs

- **RQ2：**HistGradientBoostingRegressor 是否優於 normalized-move persistence 與 Ridge？
- **RQ3：**模型能否在多個歷史 outer periods 中，可靠地將 ticker-sessions 由低到高排序？
- **RQ4：**預測在 ticker、time、stock-volatility regime 與 market regime 間是否穩健？
- **RQ5（optional）：**timestamp-safe Financial NLP features 是否提供 market-only features 以外的
  incremental value？

RQ5 不阻塞核心研究，也不要求 positive result。

## 5. Three Active Tracks

### Track A — Continuous Volatility-Surprise Forecasting

- 使用 leakage-safe price、volume、volatility、compact technical 與 TAIEX context features；
- 預測下一交易日 stock-normalized volatility surprise 連續值；
- 以 nested／rolling-origin historical OOS protocol 評估；
- 強調 ranking、decile lift、時間與 ticker robustness；
- 產出 continuous score、historical percentile 與 communication band。

### Track B — Financial NLP Intelligence

- 保留 pinned English FinBERT polarity pipeline；
- 保留 Chinese/Taiwan diagnostic failures、FSC corpus、BERT/MacBERT feasibility、TWSE
  announcements、weak supervision、market reaction、source governance 與 Eland HOLD；
- 中文 sentiment 不支援時輸出 `unsupported`／`abstain`，不偽造 polarity probability；
- 可提供 entity/event metadata、keyphrases、embedding、retrieval、related events 與 structured
  summary；
- optional F9 只在 timestamp-safe features 已可用時執行 paired ablation。

### Track C — Financial Intelligence Product

- Python backend 擁有 ingestion、features、ML、NLP、evaluation、inference、database 與 jobs；
- GAS／LINE 只作 transitional adapter、event routing、API calls、reply/push/Flex UX；
- UI 顯示 relative volatility-surprise score、percentile、band、context 與 recent intelligence；
- 不把 ML、NLP、秘密或多使用者資料邏輯搬回 GAS。

## 6. Frozen Primary Target

Target version：`next_session_stock_normalized_abs_log_return_v1`。

對 ticker `i`、feature session `t` 與下一個實際交易 session `t+1`：

```text
r(i,s)       = ln(adjusted_close(i,s) / adjusted_close(i,s-1))
sigma20(i,t) = population_std(r(i,t-19), ..., r(i,t)); ddof = 0
y(i,t+1)     = abs(ln(adjusted_close(i,t+1) / adjusted_close(i,t))) / sigma20(i,t)
```

規則：

- denominator 是截至 `t` 的 20 個 adjusted-close log-return transitions，post-close `t` 可得；
- `t+1` adjusted close 只存在 target numerator；
- `t+1` 必須是下一個 TAIEX observed exchange session，不得用更晚資料替補；
- `sigma20 <= 1e-8` 或任何 non-finite component 時，該 row abstain 並報告 exclusion count；
- 不 clip target、不用 epsilon 靜默替換 denominator；
- target 量化至 `1e-12`；
- trainable models 對 `log1p(y)` fit，評估前以 `max(0, expm1(prediction))` 回到原尺度；
- primary target 在任何模型訓練前固定，不依 F4/F5 指標更換。

此公式重用 M2/M9 已實作、通過 future-mutation test 的 normalized continuous outcome，僅新增明確
near-zero denominator gate。

Secondary robustness outcomes 固定為：

1. `next_abs_log_return`；
2. `next_high_low_log_range`；
3. `next_parkinson_volatility`；
4. `next_abs_log_return - sigma20(i,t)` additive surprise。

它們不得在看過 model results 後取代 primary target。

## 7. Existing Historical Data Coverage

已實際讀取本機 immutable snapshot，而非假設期間：

- market dataset SHA-256：
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`；
- 40,691 個股 OHLCV rows、10 tickers；
- 4,080 TAIEX benchmark sessions；
- stock/benchmark observed coverage：2010-01-04–2026-08-26；
- 既有 pre-2025 feature snapshot：28,690 rows，2011-01-03–2024-12-30；
- stock provider：Yahoo research adapter；benchmark：FinMind TAIEX total-return index。

F2 已使用相同 raw snapshot lineage 重建涵蓋所有 eligible history 的 final-study dataset：38,290
candidate rows 中 32,357 eligible、5,933 明確排除，feature dates 為
2011-01-03–2026-08-25。Dataset SHA-256 為
`2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`。排除以 provider/benchmark
缺 bar 為主，沒有 near-zero/non-finite target；完整 raw-free 結果見
`research/evaluation/f2_historical_dataset_result.md`。

### Final dataset row contract

版本：`final-volatility-surprise-dataset-v1`。每列包含 ticker、feature session、exact target session、
timezone-aware information cutoff、fixed feature mapping、continuous target 與 source lineage。
`(ticker, feature_session)` 必須唯一。禁止 random split、duplicate identity、跨缺漏 forward fill、
global preprocessing 或 raw provider data commit。

## 8. Compact Feature Contract

重用 `risk-features-v1` 的 23 features，F3 逐欄重新稽核 availability：

- **Price：**returns 1/5/10/20、overnight gap、MA deviation 5/20；
- **Volume：**log volume change、volume z-score20、zero-volume flag；
- **Volatility/range：**volatility5/20、current range、ATR14、Parkinson mean5；
- **Technical：**RSI14、MACD12/26、signal9；
- **Market：**TAIEX return1/20、volatility20、stock-minus-market return1、drawdown20。

所有 window 結束於 `t`。v1 不做 automated feature selection，不新增大量重複 technical
indicators。完整 finite row 才可進模型；缺值一律 abstain/report。NLP 不屬 core feature set。

## 9. Nested / Rolling-Origin Evaluation

禁止 random split。Outer training target 必須在 evaluation start 前完成，boundary overlap row
必須 purge。

| Outer fold | Training history | Historical evaluation period |
| --- | --- | --- |
| `outer_2017_2018` | 2011–2016 | 2017–2018 |
| `outer_2019_2020` | 2011–2018 | 2019–2020 |
| `outer_2021_2022` | 2011–2020 | 2021–2022 |
| `outer_2023` | 2011–2022 | 2023 |
| `outer_2024` | 2011–2023 | 2024 |
| `outer_2025` | 2011–2024 | 2025 |
| `outer_2026_partial` | 2011–2025 | 2026-01-01–2026-08-26 |

每個 outer training history 內，以最近三個完整年度作 one-year inner validation：

| Outer | Inner validation years |
| --- | --- |
| 2017–2018 | 2014, 2015, 2016 |
| 2019–2020 | 2016, 2017, 2018 |
| 2021–2022 | 2018, 2019, 2020 |
| 2023 | 2020, 2021, 2022 |
| 2024 | 2021, 2022, 2023 |
| 2025 | 2022, 2023, 2024 |
| 2026 partial | 2023, 2024, 2025 |

Inner selection primary 是 mean Spearman，secondary 是 mean MAE；再依 worst-inner Spearman、
lower complexity 與 deterministic parameter order tie-break。Outer block 不參與 hyperparameter、
scaler 或 preprocessing fit。

## 10. Frozen Model Set

### Model 0 — Naive persistence

`abs(return_log_1) / max(volatility_log_return_20, 1e-8)`，只使用 `t` 已知 feature，不 fit。

### Model 1 — Ridge Regression

Fold-local StandardScaler；alpha `[0.1, 1, 10, 100]`。

### Model 2 — HistGradientBoostingRegressor

Main nonlinear candidate：learning rate `[0.03, 0.05]`、max_iter `200`、max_leaf_nodes
`[15,31]`、min_samples_leaf `[20,50]`、L2 `[0,1]`、early stopping off、seed `20260827`。

XGBoost 未列入 v1，因 dependency 不存在且尚無 incremental-value justification。LSTM／Transformer
等 neural price models 禁止加入 F1 model set。

### Final model selection

以最高 mean outer-fold Spearman 為 primary。差距 `<= 0.01` 視為 practical tie；tie 時依 mean outer
MAE、worst outer Spearman、implementation complexity 決定，不能用單一幸運年度選 winner。

## 11. Metrics, Ranking and Robustness

### Regression

- MAE；
- RMSE；
- R²。

### Ranking

- Spearman rank correlation／rank IC；
- top-decile lift ratio；
- top-quintile lift ratio；
- realized primary target by predicted-score decile。

對 outer fold 中最高預測 fraction `q`：

```text
lift(q) = mean(realized primary target in predicted top q)
          / mean(realized primary target in the full outer fold)
```

Primary target 非負；若 fold-wide mean 為零／undefined，lift 回報 undefined，不補值。Top group 使用
`ceil(q*n)`，tie order 固定為 prediction descending、feature date ascending、ticker ascending。

每 fold 建立十個 equal-frequency risk buckets，報告 count、mean prediction、realized mean/median
與 uncertainty。完美 monotonicity 不是驗收條件，違反趨勢的 bucket 必須保留。

### Robustness

依 outer fold、ticker、historical stock-volatility regime、defensible market regime 與 predicted
decile 報告 MAE、RMSE、Spearman、top-decile lift。Regime cutoff 只能 fit current historical
training。Subgroup 不得再調參。

樣本足夠時以 feature-session cluster bootstrap 1,000 次、seed `20260827`、95% percentile interval
呈現 uncertainty。

## 12. Product Score and UX

F7 inference contract：ticker、`as_of_date`／information cutoff、predicted volatility-surprise
score、historical percentile、LOW／MODERATE／HIGH／VERY HIGH band、model version 與
feature-pipeline version。

Band reference 是 selected model pooled historical outer OOF predictions，cutoffs 預先固定為
50th／80th／95th percentiles。Band 是 presentation/ranking，不是 training label。

UI 文案：

> This is a relative volatility-surprise risk score, not a prediction of price direction.

並標示 research signal only、not investment advice、not guaranteed future volatility。

## 13. Exploratory Research History — Frozen Binary Track A

M1–M3 的 market/target/feature engineering 可重用；M4–M11 的 binary classifier 研究全部保留為
problem-formulation evidence。不得刪除舊 configs、reports、artifacts 或 hashes。

- **M6：**五個 2017–2024 folds 選出 Logistic + prequential Platt + 0.10；candidate manifest
  `951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`。
- **M7：**3,647 rows；recall 0.508、precision 0.180、MCC 0.155、PR-AUC 0.189、Brier 0.0926。
  Normalized separation 正、raw outcomes 較低。Evaluation SHA
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`；禁止重跑。
- **M8：**揭露 ticker/time/regime heterogeneity；analysis SHA
  `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`。
- **M9：**raw aggregate/regime reversal；normalized/additive surprise 更一致；analysis SHA
  `5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2`。
- **M10：**development OOF 0.09/0.11/0.13 trade-offs；analysis SHA
  `21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c`。
- **M11：**LOW 0.12／MIDDLE 0.10／HIGH 0.08 降低 dispersion 但 MCC 下降；analysis SHA
  `76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88`。

Binary labels、classifier thresholds、screening/precision modes、regime thresholds/classifiers 不再是
final completion path 或 production model。這些結果是 final continuous formulation 的實證動機。

## 14. Track B Evidence Freeze

必須保留：

- `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43` 與 English outputs；
- Chinese diagnostics macro-F1 0.320/0.357/0.442/0.592/0.640，無候選通過 gate；
- FSC filtered 6,021-record corpus 與 five-archive audit；
- MacBERT/BERT-base-Chinese feasibility、200-step pilot、frozen BERT-base-Chinese representation；
- TWSE announcement、market reaction、weak supervision、TEJ/TWSE/FinMind audits；
- Eland `HOLD / excluded from active modeling` rejection record。

不得宣稱 validated Chinese sentiment、人工 gold truth 或 causal impact。Eland 不得進 training、
adaptation、voting、evaluation、feature construction 或 corpus merge。

## 15. Final Study Milestones F1–F12

1. **F1 — Final Research Protocol Freeze：**凍結 questions、target、features、outer/inner
   protocol、models、metrics、ranking、claims、schema/tests。**本次 planning scope 完成。**
2. **F2 — Historical Dataset Rebuild：**使用 existing snapshot 重建 all-eligible continuous
   dataset；保存 lineage、coverage、quality、exclusions、hash 與 fold counts。**完成。**
3. **F3 — Volatility-Surprise Target & Feature Audit：**final target builder、secondary outcomes、
   feature dictionary、mutation/duplicate/next-session/leakage tests。**完成；coverage audit 發現
   calendar-year／2017–2018 fold 時間集中，屬需保留的資料限制。**
4. **F4 — Baselines & Candidate Models：**persistence、Ridge、HGB regression，全部 fold-local。
   **完成實作與 synthetic reproducibility tests；尚未跑歷史 outer evaluation。**
5. **F5 — Nested / Rolling-Origin Evaluation：**inner selection、七個 outer folds、immutable OOF。
   **完成；20,637 個 historical OOS rows、61,911 個三模型 OOF predictions，未選 final model。**
6. **F6 — Ranking & Robustness Analysis：**metrics、deciles、lift、ticker/time/regime、bootstrap。
   **完成；Ridge/HGB pooled deciles 皆 9/9 上升，所有 outer folds/tickers/regimes ranking 為正，
   但年度 monotonicity 與 magnitude fit 仍有限，未選 final model。**
7. **F7 — Final Research Model Freeze：**依 frozen rule 選 model、full-history research fit、artifact
   與 inference contract；不宣稱 prospective accuracy。**完成：Ridge alpha 100、32,357 rows、
   safe JSON artifact、historical percentile/bands；尚未部署。**
8. **F8 — Financial NLP Intelligence：**English FinBERT 與 abstention-safe Taiwan intelligence。
   **完成：統一輸出契約、pinned revision guard、中文 polarity abstention、TWSE metadata 與
   deterministic event proxy 分離、7/7 歷史證據 hash 驗證；無模型推論/訓練/部署。**
9. **F9 — Optional NLP Incremental-Value Study：**same folds/budget paired ablation；不阻塞。
10. **F10 — FastAPI / Backend Integration：**score、percentile、band、lineage、intelligence APIs。
    **完成：F7 safe-JSON lazy inference、F8 database-only intelligence、strict schemas、lineage
    guards、structured errors；無外部 API/訓練/部署，F9 未執行。**
11. **F11 — LINE / Dashboard Demo：**relative-risk score、context、intelligence、disclaimers。
    **完成：Streamlit 受控離線 fixture＋loopback-only F10 client；未修改 LINE/GAS、未部署。**
12. **F12 — Portfolio Finalization：**workflow、comparison、visuals、robustness、abstract、demo、limits。

## 16. Definition of Done

Final completion requires：reproducible final dataset、frozen continuous target、`t`-only features、
persistence/Ridge/HGB comparison、nested temporal evaluation、MAE/RMSE/R²/Spearman/decile/lift、
ticker/time/regime robustness、selected research artifact、continuous inference、honest NLP
intelligence、API/demo path、immutable historical evidence、no secrets/private/restricted data or
false investment claims。

Not required：another six-month／126-session holdout、binary classifier success、threshold mode
deployment、regime classifiers、validated Chinese sentiment、positive NLP lift、TEJ AP11、trading
profitability。Prospective validation 是自然未來資料累積後的 external future work。

## 17. Security and Automated Research Safety

- no random split、future feature、global preprocessing、outer leakage、duplicate ticker/date；
- exact next exchange session and timezone-aware cutoff；
- rolling windows end at `t`；`t+1` mutation cannot change `t` feature hash；
- inner selection contained inside outer training；
- dataset/config/model/OOF hashes deterministic where feasible；
- secrets 只進 ignored `.env`；raw/private/restricted data 保持 ignored；
- GAS 不修改、ML 不搬入 GAS、無 deploy 或 automatic commit/push。

## 18. Immediate Execution Boundary

F1–F8、F10 與 F11 已完成；F9 維持 optional/not run。F7 依 frozen practical-tie rule 以較低 mean outer MAE 選 Ridge，再以 2023–2025
training-history-only validation 選 alpha 100，並以 32,357 rows 建立 safe JSON artifact。這不代表
prospective accuracy 或精準 magnitude prediction。M7 evaluation sequence 永久為 1，禁止呼叫或
重跑 M7。不得回頭利用 F6 subgroup 結果調參、修改 working GAS、deploy、commit 或 push。

F10 已把 F7/F8 接到 versioned FastAPI research endpoints。F11 再以 Streamlit 建立受控公開展示，
預設只讀固定合成 fixture，也可選擇 loopback-only F10 API；兩種模式都不等同即時市場證據。
下一個最小單元是 **F12 — Portfolio Finalization**。不得自動修改或部署既有 GAS。
