# Financial AI Assistant — Authoritative Handoff

Last revised: 2026-08-28

Direction: **continuous stock-normalized volatility-surprise forecasting**

Current unit: **F11 controlled Streamlit Dashboard complete**
Next executable unit: **F12 only after user review/approval**

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
- **F4:** persistence/Ridge/HGB regressors — implementation complete.
- **F5:** nested rolling-origin evaluation and OOF predictions — complete; no final winner selected.
- **F6:** ranking/decile/lift/robustness — complete; no final winner selected.
- **F7:** final research artifact and inference freeze — complete; Ridge alpha 100, not deployed.
- **F8:** Financial NLP Intelligence — complete; abstention-safe contract, no model inference.
- **F9:** optional NLP incremental-value study — not run; non-blocking.
- **F10:** FastAPI/backend integration — complete; local only, not deployed.
- **F11:** controlled Streamlit dashboard complete; LINE/GAS unchanged.
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

## F5 ARTIFACTS AND RESULT

- Evaluation config: `research/configs/final_nested_temporal_evaluation.v1.json`.
- Evaluator: `research/modeling/final_temporal_evaluation.py`.
- CLI: `jobs/final_temporal_evaluation.py` / `financial-ai-final-temporal-evaluation`.
- Safety tests: `tests/unit/test_final_temporal_evaluation.py`.
- Public result: `research/evaluation/f5_nested_temporal_evaluation_result.md`.
- Local immutable OOF: `.tools/evaluation/f5-final-regression-oof-v1/predictions.json`.
- Canonical F5 config SHA-256:
  `3ebf45f6054d40724970f1be2f1c0bbf6588cb085b7bafe0196077cc304256af`.
- Canonical OOF SHA-256:
  `b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7`.

Seven folds produced 20,637 unique historical evaluation rows and 61,911 three-model OOF
predictions. Mean outer Spearman was 0.0608 for persistence, 0.1940 for Ridge and 0.1863 for HGB.
Ridge and HGB are inside the frozen 0.01 practical-tie margin. Their average R-squared values were
near zero/slightly negative, so the current evidence supports a modest ranking signal more than
accurate magnitude prediction. F5 intentionally selected no final model.

## F6 ARTIFACTS AND RESULT

- Analysis config: `research/configs/final_ranking_robustness.v1.json`.
- Analyzer: `research/evaluation/final_ranking_robustness.py`.
- CLI: `jobs/final_ranking_robustness.py` / `financial-ai-final-ranking-robustness`.
- Safety tests: `tests/unit/test_final_ranking_robustness.py`.
- Public result: `research/evaluation/f6_ranking_robustness_result.md`.
- Local aggregate analysis: `.tools/evaluation/f6-final-ranking-robustness-v1/analysis.json`.
- Canonical F6 config SHA-256:
  `d860f42a3e47d8b136d93a652be6952de786bcdd5cfd94131b7069967ce9c939`.
- Canonical F6 analysis SHA-256:
  `8fd2fdc84f65fb47b6bc87df4b662c4bbd5a9ec8c82d41de4cdd3825b6364e70`.

Ridge/HGB mean top-decile lift was 1.354/1.361 and mean Spearman was 0.194/0.186. Both candidates
had positive ranking and lift above one in every outer period, ticker and training-defined regime.
Their pooled outer-assigned deciles were 9/9 non-decreasing, but individual folds reached only 5–9
steps and the model-level bootstrap intervals overlap. F6 did not select a final model.

## F7 ARTIFACTS AND RESULT

- Freeze config: `research/configs/final_model_freeze.v1.json`.
- Model/inference implementation: `research/modeling/final_research_model.py`.
- CLI: `jobs/final_model_freeze.py` / `financial-ai-final-model-freeze`.
- Safety tests: `tests/unit/test_final_research_model.py`.
- Public result: `research/evaluation/f7_final_research_model_result.md`.
- Local safe JSON artifact: `.tools/models/f7-final-ridge-research-v1/model.json`.
- Canonical F7 config SHA-256:
  `d87b335e3a03382ca7f0e45bb80fdb862e9017b93756a40171d61936410dc167`.
- Canonical model artifact SHA-256:
  `279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de`.

Ridge/HGB were a practical tie under the frozen 0.01 Spearman margin. Ridge was selected by the
first applicable tie-break, lower mean outer MAE. Temporal validation over 2023/2024/2025 selected
alpha 100. The final research fit used all 32,357 eligible rows and persisted scaler/model state plus
20,637 Ridge OOF reference scores as safe JSON. It was not deployed and makes no prospective claim.

## F8 ARTIFACTS AND RESULT

- Frozen config: `research/configs/financial_nlp_intelligence.v1.json`.
- Contract assembler: `pipelines/intelligence/financial_nlp.py`.
- CLI: `jobs/financial_nlp_intelligence.py` / `financial-ai-nlp-intelligence`.
- Safety tests: `tests/unit/test_financial_nlp_intelligence.py`.
- Public result: `research/evaluation/f8_financial_nlp_intelligence_result.md`.
- Local aggregate analysis: `.tools/evaluation/f8-financial-nlp-intelligence-v1/analysis.json`.
- Canonical F8 config SHA-256:
  `de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4`.
- Canonical F8 analysis SHA-256:
  `8994a66e2fef70da2ad16d54cb3698ac8e2f14badad4e9237a03e2669b97ab42`.

Seven historical NLP evidence files passed byte-hash verification. English text is either scored
with the exact pinned FinBERT revision or remains `ELIGIBLE_NOT_SCORED`; Chinese/Taiwan polarity
always abstains with null probabilities. Official metadata and deterministic event/impact proxies
are separate from sentiment and are not ground truth. The controlled audit ran no model, API, LLM,
manual review, training or deployment, and persisted no fixture rows/private text.

## F10 ARTIFACTS AND RESULT

- Frozen config: `research/configs/backend_integration.v1.json`.
- Config guards: `research/planning/backend_integration.py`.
- Prediction service: `backend/app/services/research_prediction.py`.
- Intelligence service/repository: `backend/app/services/intelligence.py` and
  `backend/app/repositories/intelligence.py`.
- API/schema: `backend/app/api/research.py` and `backend/app/schemas/research.py`.
- Audit CLI: `jobs/backend_integration.py` / `financial-ai-backend-integration`.
- Tests: `tests/unit/test_backend_integration_protocol.py` and
  `tests/integration/test_research_api.py`.
- Public result: `research/evaluation/f10_backend_integration_result.md`.
- Canonical F10 config SHA-256:
  `b4367815b484352375b6693d91b44298b8e4dc3b84bf0a3c69f956f97175a4f2`.
- Canonical F10 analysis SHA-256:
  `dc26d6f13e07c27e8ec32b6da8d06ac6fb1fed9b5fff32040a9d69221394b5fb`.

The POST prediction endpoint validates the exact 23-feature F7 contract and returns score,
percentile, band and lineage. The GET intelligence endpoint reads only stored news/ticker/pinned
English sentiment rows and preserves Chinese abstention. F10 makes no external request, trains no
model, exposes no private portfolio data, modifies no GAS and performs no deployment. F9 was not
run and no NLP-lift claim exists.

## SAFETY AND NEXT ACTION

Do not rewrite F5/F6/F7/F8/F10 evidence, retune the frozen Ridge from subgroup results, rerun M7,
fabricate Chinese sentiment, create a fake sealed test, modify working GAS, deploy, commit or push
during the F8 stop boundary.

Run and preserve automated checks for random-split prohibition, exact next session, `t+1` mutation,
rolling shift, target-field exclusion, duplicate ticker/date, inner/outer isolation, fold-local
preprocessing and exact hashes.

F3 found no ticker or known-volatility-regime concentration, but calendar years
2012/2013/2016/2017/2019 and outer fold 2017–2018 triggered the predeclared coverage rule. The
warning therefore remains `DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION`; it is not a
target/leakage/code defect. See `research/evaluation/f3_target_feature_coverage_audit_result.md`.

F4 implemented 1 persistence, 4 Ridge and 16 HGB parameterized candidates under the frozen F1
grid. Synthetic tests confirm training-only scaling, temporal-overlap rejection and deterministic
fit manifests/predictions. See `research/evaluation/f4_regression_candidates_result.md`.

## F11 ARTIFACTS AND RESULT

- Dashboard：`demo/app.py`。
- Strict contracts／safe API client／presentation：`demo/contracts.py`、`demo/client.py`、
  `demo/presentation.py`。
- Deterministic builder／controlled fixture：`demo/fixture_builder.py`、
  `demo/fixtures/controlled_dashboard_demo.v1.json`。
- Frozen config：`research/configs/dashboard_demo.v1.json`。
- Tests：`tests/unit/test_dashboard_demo.py`、`tests/unit/test_dashboard_client.py`、
  `tests/integration/test_streamlit_dashboard.py`。
- Public result：`research/evaluation/f11_dashboard_demo_result.md`。
- Canonical config SHA-256：
  `0f70c88b6ea3b6e21177ae2fce6a4bef17d1b02a89a0dd7d491d425663ebc267`。
- Canonical fixture SHA-256：
  `c55f546ebe9ee94f616d518c205c18acb6b35683436dce1a312e7849c2935c06`。

F11 預設完全離線且只顯示合成資料；本機 API 模式限 plain-HTTP loopback origin。合成分數由
frozen F7 artifact 產生，但不是實際 2330 觀測或 performance evidence。中文 polarity 維持
abstain，英文範例維持 eligible-not-scored。未修改 GAS、未部署、未呼叫 provider/LLM。

After user review, the next minimum executable unit is **F12 — Portfolio Finalization**. F9 remains
optional and non-blocking; Track A completion does not depend on NLP lift.
