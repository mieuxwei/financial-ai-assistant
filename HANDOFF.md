# Financial AI Assistant — Authoritative Handoff

Last revised: 2026-08-27

Direction: **continuous stock-normalized volatility-surprise forecasting**

Current unit: **F3 target/feature/coverage audit complete**
Next executable unit: **F4 only after user review/approval**

## ACTIVE PROJECT DIRECTION

Final English title:

> Stock-Normalized Volatility Surprise Forecasting with Financial NLP Intelligence

Final Chinese title:

> 基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統

Product name remains **Financial AI Assistant**.

Primary research question:

> Can leakage-safe price, volume, volatility and market-context features forecast next-session
> volatility surprise relative to each stock's own historical volatility context?

Track A now predicts a continuous next-session stock-normalized volatility-surprise score. Track B
remains Financial NLP Intelligence. Track C remains the Python/FastAPI plus slim LINE/GAS product.

## WHY THE FORMULATION CHANGED

The binary `HIGH_RISK`/`NORMAL` study is not deleted and is not described as a failure. It is now
**Exploratory Binary-Risk Research / Problem-Formulation Evidence**.

The exploratory work showed substantial threshold-dependent precision/recall trade-offs and
regime-dependent operating behavior. M11 reduced cross-regime recall/specificity dispersion with
LOW 0.12／MIDDLE 0.10／HIGH 0.08, but overall MCC fell. M9 also showed that aggregate raw absolute-
volatility comparisons reversed after stock-volatility conditioning, while normalized and additive
surprise outcomes were much more consistent.

Authoritative wording:

> The exploratory binary-risk formulation revealed substantial threshold and regime sensitivity.
> Conditional analysis showed that the more stable signal was stock-relative volatility surprise
> rather than unconditional absolute volatility. The final study therefore reformulates the task
> as continuous stock-normalized volatility-surprise forecasting.

## RESEARCH INTEGRITY BOUNDARY

The final study is:

`RETROSPECTIVE_LEAKAGE_AWARE_HYPOTHESIS_INFORMED_FINAL_STUDY`

The historical data has already informed research decisions. Therefore no historical period may
be presented as a new pristine untouched test, prospective validation, independent external
validation or preregistered confirmation.

Previously inspected 2025–2026 rows may be included as historical outer rolling-origin periods,
but must be called retrospective historical OOS evidence. The project no longer waits for a new
126-session/six-month holdout. Naturally future data remains useful **Future External Validation**,
not a completion requirement.

Never rerun M7. Evaluation sequence remains exactly one.

## FROZEN PRIMARY TARGET

Version: `next_session_stock_normalized_abs_log_return_v1`.

```text
r(i,s)       = ln(adjusted_close(i,s) / adjusted_close(i,s-1))
sigma20(i,t) = population_std(last 20 adjusted-close log returns ending at t); ddof=0
y(i,t+1)     = abs(ln(adjusted_close(i,t+1) / adjusted_close(i,t))) / sigma20(i,t)
```

- `sigma20` is available post-close at `t`.
- `t+1` is the exact next observed TAIEX exchange session.
- `t+1` adjusted close is target-only.
- Exclude/report rows when `sigma20 <= 1e-8` or any component is non-finite.
- Do not clip the target or silently replace the denominator.
- Quantize to `1e-12`.
- Trainable models fit `log1p(y)` and evaluate `max(0, expm1(prediction))` on the original scale.

This reuses the existing leakage-tested normalized continuous outcome and adds a frozen near-zero
gate. Secondary outcomes are raw absolute log return, high-low log range, Parkinson proxy and
additive absolute-return surprise versus `sigma20`.

## VERIFIED HISTORICAL COVERAGE

Read-only local inspection found:

- market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`;
- 40,691 stock rows across ten tickers;
- 4,080 TAIEX benchmark sessions;
- observed market coverage 2010-01-04–2026-08-26;
- existing pre-2025 feature dataset 28,690 rows, 2011-01-03–2024-12-30;
- stock provider Yahoo research adapter and FinMind TAIEX total-return benchmark.

F2 produced 32,357 eligible rows from 38,290 candidates and excluded 5,933 rows under the frozen
strict-session contract. Feature coverage is 2011-01-03–2026-08-25 and the immutable dataset
SHA-256 is `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.
No preprocessing/model/binary label was created. See
`research/evaluation/f2_historical_dataset_result.md`.

## FROZEN TEMPORAL DESIGN

Outer rolling-origin periods:

| Fold | Train | Historical outer evaluation |
| --- | --- | --- |
| `outer_2017_2018` | 2011–2016 | 2017–2018 |
| `outer_2019_2020` | 2011–2018 | 2019–2020 |
| `outer_2021_2022` | 2011–2020 | 2021–2022 |
| `outer_2023` | 2011–2022 | 2023 |
| `outer_2024` | 2011–2023 | 2024 |
| `outer_2025` | 2011–2024 | 2025 |
| `outer_2026_partial` | 2011–2025 | 2026-01-01–2026-08-26 |

Each outer fold selects hyperparameters only inside its training history using the latest three
complete one-year inner validations:

- 2014/2015/2016;
- 2016/2017/2018;
- 2018/2019/2020;
- 2020/2021/2022;
- 2021/2022/2023;
- 2022/2023/2024;
- 2023/2024/2025.

Inner primary selection metric is mean Spearman, then mean MAE, worst-inner Spearman, lower
complexity and deterministic parameter order. Outer validation never fits imputation, scaling,
features, transforms or hyperparameters. Boundary targets overlapping evaluation are purged.

## FROZEN MODEL AND METRIC SET

Models:

1. normalized-move persistence baseline;
2. Ridge Regression with fold-local StandardScaler and alpha `[0.1,1,10,100]`;
3. HistGradientBoostingRegressor with the small grid frozen in
   `research/configs/final_volatility_surprise_study.v1.json`.

XGBoost is excluded from F1 because the dependency and incremental value are not justified. Neural
price models are not allowed.

Required metrics:

- MAE, RMSE, R²;
- Spearman/rank IC;
- top-decile and top-quintile lift ratios;
- realized target by predicted-score decile;
- outer-fold/ticker/stock-regime/market-regime robustness;
- feature-session cluster bootstrap uncertainty where practical.

Select the final model by mean outer Spearman. Differences `<=0.01` are practical ties; then prefer
lower mean MAE, higher worst-fold Spearman and lower complexity. One lucky period cannot select a
winner.

## PRODUCT OUTPUT BOUNDARY

The final inference contract will return ticker, as-of/cutoff, predicted surprise score, historical
percentile, communication band, model version and feature-pipeline version.

LOW/MODERATE/HIGH/VERY HIGH are presentation bands from selected-model historical OOF prediction
percentiles 50/80/95. They are not classifier labels. Product copy must state:

> This is a relative volatility-surprise risk score, not a prediction of price direction.

Also state research-only, not investment advice and no guaranteed future volatility.

## EXPLORATORY / FROZEN BINARY RESEARCH

Preserve every historical report, config, model artifact and hash:

- M6 candidate manifest:
  `951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`.
- M7 sealed evaluation:
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`.
- M8 robustness analysis:
  `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`.
- M9 conditional analysis:
  `5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2`.
- M10 operating-point analysis:
  `21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c`.
- M11 regime-threshold analysis:
  `76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88`.

Historical facts remain:

- M7: 3,647 rows, recall 0.508, precision 0.180, MCC 0.155, PR-AUC 0.189, Brier 0.0926;
- M8: material ticker/time/regime heterogeneity;
- M9: raw aggregate/within-regime reversal and stable normalized/additive surprise;
- M10: development thresholds 0.09/0.11/0.13 with substantial trade-offs;
- M11: 73/125,000 eligible triplets, selected 0.12/0.10/0.08, lower dispersion but lower MCC.

These are not the final production model. Do not delete, rerun, retrospectively rewrite or use
them to claim a pristine final test.

## TRACK B — PRESERVE ALL NLP EVIDENCE

Preserve:

- `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43` and English polarity outputs;
- historical 12-item English sanity evidence only;
- Chinese diagnostic macro-F1 0.320/0.357/0.442/0.592/0.640; no candidate passed the gate;
- zero-manual-label/abstention protocol;
- filtered 6,021-record FSC family-isolated corpus;
- BERT-base-Chinese/MacBERT feasibility and 200-step pilot;
- frozen BERT-base-Chinese representation candidate, not sentiment truth;
- TWSE announcement processing, market reaction and weak-supervision infrastructure;
- TWSE/FinMind/TEJ source and licensing audits;
- Eland permanent `HOLD / excluded from active modeling` record.

Chinese sentiment may abstain. Never fabricate Positive/Neutral/Negative probabilities. Optional
F9 NLP incremental-value work uses the same outer folds and model budget and cannot block F12.

## ACTIVE F-SERIES

- **F1:** protocol/config/schema/safety-test freeze — planning scope complete.
- **F2:** historical continuous dataset rebuild — complete.
- **F3:** final target, feature and coverage-bias audit — complete with temporal concentration.
- **F4:** persistence/Ridge/HGB regressors — next after approval.
- **F5:** nested rolling-origin evaluation and OOF predictions.
- **F6:** ranking/decile/lift/robustness.
- **F7:** final research artifact and inference freeze.
- **F8:** Financial NLP Intelligence.
- **F9:** optional NLP incremental-value study.
- **F10:** FastAPI/backend integration.
- **F11:** LINE/dashboard demo.
- **F12:** portfolio finalization.

No longer blocking: M12 six-month wait, a new untouched holdout, binary classifier success,
regime-threshold deployment, validated Chinese sentiment, positive NLP lift, TEJ AP11 or trading
profitability.

## F1 ARTIFACTS

- Plan: `PROJECT_PLAN.md`.
- Protocol: `docs/final_volatility_surprise_study_protocol.md`.
- Migration map: `docs/final_study_migration.md`.
- Machine config: `research/configs/final_volatility_surprise_study.v1.json`.
- Config schema/guards: `research/planning/final_study_protocol.py`.
- Safety tests: `tests/unit/test_final_study_protocol.py`.
- Canonical F1 config SHA-256:
  `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66`.

## F2 ARTIFACTS

- Builder: `pipelines/features/final_study_builder.py`.
- CLI: `jobs/final_study_dataset.py` / `financial-ai-final-study-dataset`.
- Safety tests: `tests/unit/test_final_study_dataset_builder.py`.
- Public result: `research/evaluation/f2_historical_dataset_result.md`.
- Local dataset: `.tools/datasets/final-volatility-surprise-dataset-v1/dataset.json`.
- Dataset SHA-256:
  `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.

## SAFETY AND NEXT ACTION

Do not train regression models, generate F5 results, choose an F7 winner, rerun M7, create a fake
sealed test, modify working GAS, deploy, commit or push during F2.

Run and preserve automated checks for random-split prohibition, exact next session, `t+1` mutation,
rolling shift, target-field exclusion, duplicate ticker/date, inner/outer isolation, fold-local
preprocessing and exact hashes.

F3 found no ticker or known-volatility-regime concentration, but calendar years
2012/2013/2016/2017/2019 and outer fold 2017–2018 triggered the predeclared coverage rule. The
warning therefore remains `DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION`; it is not a
target/leakage/code defect. See `research/evaluation/f3_target_feature_coverage_audit_result.md`.

After user review, the next minimum executable unit is **F4 — Baselines & Candidate Models**. F3
has not automatically begun F4 or trained a model.
