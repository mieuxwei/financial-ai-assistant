# Final Study Migration Map

Migration date: 2026-08-28
Status: historical F-series mapping; R0 reclassifies F11 as F11A complete / F11B pending and makes
B1 the next executable unit. See `docs/r0_project_rebaseline_protocol.md`.

## Migration principle

The binary-risk study is not deleted or called a failure. It is reclassified as **Exploratory
Binary-Risk Research / Problem-Formulation Evidence**. It established temporal infrastructure and
revealed threshold sensitivity, regime instability and the more stable stock-relative target.

The active final study is **continuous stock-normalized volatility-surprise forecasting**. All
historical periods are retrospective rolling-origin evidence; prospective external validation is
future work rather than a portfolio completion gate.

## Old M-series to final F-series

| Existing milestone/evidence | Final status | Reuse in F-series |
| --- | --- | --- |
| M0 security, FastAPI and repository foundation | Preserved active foundation | F10–F12 integration, reproducibility and safety |
| M1 immutable OHLCV/TAIEX dataset and quality audit | Preserved reusable data foundation | F2 dataset rebuild and lineage audit |
| M2 normalized continuous outcome plus binary label | Continuous formula reused; binary threshold becomes exploratory | F3 primary target reuses normalized outcome with explicit near-zero gate |
| M3 23 leakage-safe market features | Preserved reusable feature foundation | F3 formula/availability audit and final dataset |
| M4 Logistic/naive classification baselines | Frozen exploratory binary evidence | Explains need for new Ridge/persistence regression baselines in F4 |
| M5 RF/HGB classifier comparison | Frozen exploratory negative/comparison evidence | HGB family reconsidered as a regressor under F4, without importing classifier results as regression proof |
| M6 binary walk-forward/calibration/threshold selection | Frozen exploratory temporal-method evidence | Temporal isolation patterns inform F5; old probabilities/thresholds do not train the final model |
| M7 one-time 2025–2026 sealed binary evaluation | Immutable exploratory evidence; never rerun | Period may appear only as already-inspected historical outer folds in F5 |
| M8 binary robustness/error analysis | Immutable exploratory evidence | Motivates F6 ticker/time/regime robustness reporting |
| M9 conditional/Simpson analysis | Immutable problem-formulation evidence | Direct motivation for the continuous stock-normalized target |
| M10 global operating-point study | Immutable exploratory threshold evidence | Not part of final model selection or product bands |
| M11 regime-aware threshold study | Immutable exploratory stability evidence | Demonstrates why ranking/continuous output replaces classifier threshold deployment |
| M12 prospective binary holdout plan | No longer blocks completion | Future external validation only; not an active F milestone |
| M13 optional regime classifiers | Inactive/not authorized | Not mapped into final v1 model set |
| M14 NLP Intelligence plan plus prior NLP work | Preserved parallel intelligence track | F8 Financial NLP Intelligence |
| M15 optional NLP ablation | Still optional/non-blocking | F9 optional incremental-value study |
| M16 binary risk backtest/validation | Superseded as core | F6 ranking/robustness; trading remains non-goal |
| M17 Prediction/Intelligence API | Product intent preserved | F10 FastAPI/backend integration |
| M18 LINE/GAS slimming | Product intent preserved | F11 LINE/dashboard demo; ML remains in Python |
| M19 public demo | Product intent preserved | F11–F12 controlled demo and portfolio |
| M20 portfolio finalization | Product intent preserved | F12 finalization |

## Immutable M7–M11 evidence

| Evidence | SHA-256 | Final role |
| --- | --- | --- |
| M7 sealed binary evaluation | `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe` | Historical classifier evidence; rerun prohibited |
| M8 robustness analysis | `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b` | Threshold/regime heterogeneity evidence |
| M9 conditional analysis | `5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2` | Stock-relative target motivation |
| M10 operating points | `21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c` | Precision/recall trade-off evidence |
| M11 regime thresholds | `76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88` | Stability-versus-discrimination trade-off evidence |

These hashes, reports, configs and ignored artifacts cannot be deleted, rewritten into a different
result or used to claim prospective confirmation.

## Active F-series completion path

1. **F1 — Final Research Protocol Freeze:** continuous target, folds, inner selection, models,
   metrics, claims and safety tests. **Complete at planning scope.**
2. **F2 — Historical Dataset Rebuild:** rebuild all eligible existing history with lineage,
   cutoffs, duplicate and quality audits. **Complete:** 32,357 eligible rows; dataset SHA-256
   `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.
3. **F3 — Volatility-Surprise Target & Feature Audit:** implement/freeze final dataset builder,
   target near-zero policy, feature dictionary, mutation tests and coverage-bias audit.
   **Complete with documented temporal coverage concentration.**
4. **F4 — Baselines & Candidate Models:** persistence, Ridge and HGB regressors; XGBoost excluded in
   v1 unless a separately approved protocol amendment justifies it. **Implementation complete;
   historical evaluation not run.**
5. **F5 — Nested / Rolling-Origin Evaluation:** inner temporal tuning, seven outer historical
   folds and reproducible OOF predictions. **Complete:** 20,637 evaluation rows and 61,911
   three-model OOF predictions; no final winner selected.
6. **F6 — Ranking & Robustness Analysis:** regression/ranking metrics, deciles, lift,
   ticker/time/regime diagnostics and uncertainty. **Complete:** immutable F5 OOF only, 1,000
   clustered bootstrap replicates, no retuning/final selection.
7. **F7 — Final Research Model Freeze:** frozen winner, full-history research fit, artifact and
   inference contract without prospective claim. **Complete:** Ridge alpha 100 safe-JSON research
   artifact, historical percentile/bands, not deployed.
8. **F8 — Financial NLP Intelligence:** English FinBERT and abstention-safe Taiwan announcement
   intelligence with all prior NLP evidence preserved. **Complete:** frozen product contract,
   Chinese polarity abstention, separate event proxy and 7/7 evidence-hash verification; no model
   inference or deployment.
9. **F9 — Optional NLP Incremental-Value Study:** non-blocking paired ablation. **Not run.**
10. **F10 — FastAPI / Backend Integration:** continuous score, percentile, band and intelligence
    endpoints with lineage. **Complete:** local research endpoints, strict lineage and
    database-only intelligence; not deployed.
11. **F11A — Controlled Streamlit Dashboard:** relative-risk score plus traceable intelligence and
    research disclaimers. **Complete; not deployed.**
12. **F11B — LINE/GAS Integration:** **pending** under the R0 backup/rollback boundary.
13. **F12 — Portfolio Finalization:** final narrative, comparisons, ranking visuals, limitations,
    abstract and demo script.

## Explicitly no longer blocking

- waiting six months for 126 future exchange sessions;
- creating a new untouched historical holdout after the formulation has already been informed;
- binary classifier precision/recall or regime-threshold deployment;
- validated Chinese polarity classification;
- a positive NLP incremental-value result;
- paid TEJ AP11 access;
- trading profitability.

Prospective validation after naturally future data accumulates remains valuable **future external
validation**, but it is not represented as completed and is not required for F12.
