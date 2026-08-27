# M6 Temporal Validation — Raw-Free Candidate Freeze Result

Evaluation date: 2026-08-27  
Protocol: `risk-temporal-validation-v1`  
Result: **PASS — candidate frozen, sealed test unopened**

## Fold evidence

| Fold | Train rows | Evaluation rows | HIGH_RISK | Logistic PR-AUC | RF PR-AUC | HGB PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| 2017–2018 | 11,710 | 3,420 | 333 | 0.157 | 0.154 | 0.154 |
| 2019–2020 | 15,140 | 4,220 | 435 | 0.230 | 0.203 | 0.194 |
| 2021–2022 | 19,350 | 4,530 | 455 | 0.169 | 0.168 | 0.168 |
| 2023 | 23,890 | 2,390 | 235 | 0.158 | 0.138 | 0.138 |
| 2024 | 26,270 | 2,410 | 253 | 0.186 | 0.187 | 0.180 |

Ten training rows were explicitly purged at each affected calendar boundary where the next-session
target otherwise reached the evaluation period. No overlapping target entered evaluation fitting.

## Model selection

| Model | Mean fold PR-AUC | Mean fold MCC | Mean fold recall | Mean fold Brier |
|---|---:|---:|---:|---:|
| Logistic Regression | **0.180** | **0.136** | **0.622** | 0.228 |
| Random Forest | 0.170 | 0.118 | 0.286 | 0.180 |
| HistGradientBoosting | 0.167 | 0.103 | 0.330 | **0.168** |

Logistic Regression was selected by the predeclared primary mean-fold PR-AUC rule. Tree models had
better raw Brier scores but lower ranking and HIGH_RISK sensitivity. This trade-off is preserved;
the test did not participate.

## Calibration and threshold

On folds 2–5, leakage-safe prequential Platt calibration changed pooled Brier from 0.2244 to 0.0885.
All sequential Platt coefficients were positive. At the ordinary 0.5 threshold calibration recall
would be only 0.012, demonstrating that calibrated probabilities and classification cutoff are
separate decisions.

The recall-constrained grid selected threshold 0.10:

- confusion matrix: TN 7,775; FP 4,397; FN 571; TP 807;
- HIGH_RISK recall: 0.586;
- precision: 0.155;
- MCC: 0.139;
- PR-AUC: 0.184;
- ROC-AUC: 0.657;
- Brier: 0.0885.

This threshold is now frozen. It cannot be changed after seeing sealed-test results.

## Final candidate and lineage

- Selected model: Logistic Regression with training-only StandardScaler.
- Calibration: Platt, fit from 16,970 OOF rows.
- Decision threshold: 0.10.
- Final fit: 28,690 pre-test rows through 2024-12-31.
- M3 dataset SHA-256:
  `a9898ce18a2497efaa98d22dc5e99f40bae446f175781c3c47bde92972d26bb0`.
- M6 config SHA-256:
  `9f221c5d36cf3611ed8894b4630b12f221d398cd21afe7f91d05156b08c3e276`.
- Final-fit rows SHA-256:
  `5a21544de44ffe24f0a3a6fa67281a88ec30f2cadd109bae0be66939660c5028`.
- Final model-state SHA-256:
  `893d13695b6d6f2c4267dcf190e77c7770df2f894c7894b6a0de4215cadead9d`.
- Candidate manifest SHA-256:
  `951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`.

Two consecutive full M6 runs reproduced the immutable manifest. Resource timing, detailed machine
reports and provider-derived rows remain ignored. No raw prediction row, credential, private
holding, personal information or test result appears in this public summary.

## Sealing status

- Candidate recipe frozen: **true**.
- Sealed-test feature/outcome opened: **false**.
- Sealed-test evaluation count: **0**.
- Model, calibration, feature or threshold selection after test: **prohibited**.
