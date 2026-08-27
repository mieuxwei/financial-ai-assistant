# F5 Nested / Rolling-Origin Evaluation Result

Date: 2026-08-27  
Status: **COMPLETE — retrospective historical OOS evaluation; no final model selected**

## 1. Scope and claim boundary

F5 executed the frozen F1/F4 protocol across seven chronological outer folds. Hyperparameters were
selected only from three expanding-window inner validation years contained in the corresponding
outer training history. The selected setting was then refitted on the full outer training history
and evaluated once on the later outer block.

This is a **retrospective, leakage-aware, hypothesis-informed** evaluation. The 2025 and partial
2026 blocks were previously inspected during exploratory binary-risk research and are not an
untouched sealed test, prospective validation or independent external validation.

F5 did not run F6 decile/lift/bootstrap analysis, choose the F7 final model, fit a full-history
production artifact, modify GAS, deploy, commit or push.

## 2. Frozen lineage

| Object | Canonical SHA-256 |
| --- | --- |
| F1 final-study protocol config | `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66` |
| F2 final dataset | `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c` |
| F4 regression-candidate config | `88ff58b4510cec94c0f0b5a1c895cad3bafc126bf61048d01facdfb1dbfae726` |
| F5 evaluation config | `3ebf45f6054d40724970f1be2f1c0bbf6588cb085b7bafe0196077cc304256af` |
| F5 immutable OOF predictions | `b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7` |

The canonical hashes are calculated from normalized JSON content. They are intentionally distinct
from byte-level file hashes, which also reflect whitespace/serialization layout.

## 3. Execution summary

- Outer folds: 7.
- Candidate families: normalized-move persistence, Ridge and HGB.
- Unique outer evaluation rows: 20,637.
- OOF prediction rows: 61,911 (`20,637 × 3 models`).
- Duplicate `(model, outer_fold, ticker, feature_session)` identities: 0.
- Runtime: 408.26 seconds in the local isolated environment.
- Every outer validation date is later than its training history.
- Ridge scaling was fitted inside each current training fold only.
- No outer result entered inner hyperparameter selection.
- OOF artifact reproduction check matched its recorded canonical SHA.

Large OOF/report artifacts remain git-ignored. This committed document contains only aggregate,
raw-free research evidence.

## 4. Aggregate outer-fold performance

Metrics are computed on the original, nonnegative volatility-surprise scale. Values below are the
unweighted mean/median across the seven outer folds, not a row-weighted pooled score.

| Model | Mean MAE | Median MAE | Mean RMSE | Mean R² | Mean Spearman | Median Spearman | Worst-fold Spearman |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | 0.7274 | 0.7309 | 1.0150 | -0.5834 | 0.0608 | 0.0646 | 0.0080 |
| Ridge | **0.5473** | **0.5452** | 0.8109 | -0.0086 | **0.1940** | **0.1921** | 0.1091 |
| HGB | 0.5480 | 0.5469 | **0.8096** | **-0.0054** | 0.1863 | 0.1679 | **0.1349** |

Ridge and HGB differ by approximately `0.0078` mean Spearman, inside the frozen F1 practical-tie
margin of `0.01`. Ridge has slightly lower mean MAE; HGB has slightly lower mean RMSE, less-negative
mean R² and higher worst-fold Spearman. F5 therefore records a practical tie and deliberately does
not name a final winner. F6 robustness/ranking evidence must be completed before F7 applies the
frozen selection rule.

## 5. Outer-fold detail

| Outer fold | Eval rows | Persistence MAE / Spearman / R² | Ridge MAE / Spearman / R² | HGB MAE / Spearman / R² |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2017–2018 | 3,420 | 0.7147 / 0.0863 / -0.5180 | 0.5578 / 0.1576 / 0.0137 | 0.5574 / 0.1499 / 0.0167 |
| 2019–2020 | 4,220 | 0.7309 / 0.0820 / -0.4893 | 0.5553 / 0.2109 / 0.0209 | 0.5605 / 0.1679 / 0.0072 |
| 2021–2022 | 4,540 | 0.7382 / 0.0382 / -0.6365 | 0.5452 / 0.1906 / 0.0172 | 0.5467 / 0.1811 / 0.0242 |
| 2023 | 2,390 | 0.7156 / 0.0080 / -0.7066 | 0.5252 / 0.1091 / -0.0069 | 0.5243 / 0.1349 / 0.0022 |
| 2024 | 2,420 | 0.7368 / 0.0646 / -0.6176 | 0.5450 / 0.2253 / -0.0067 | 0.5469 / 0.2288 / 0.0004 |
| 2025 | 2,106 | 0.7211 / 0.0902 / -0.5086 | 0.5440 / 0.2727 / -0.0067 | 0.5392 / 0.2801 / 0.0125 |
| 2026 partial | 1,541 | 0.7345 / 0.0564 / -0.6072 | 0.5586 / 0.1921 / -0.0915 | 0.5606 / 0.1611 / -0.1008 |

All Ridge and HGB outer-fold Spearman values are positive. Point-forecast R² is nevertheless near
zero on average and negative in some later periods. The honest interpretation is a modest,
time-varying ranking signal with weak absolute-magnitude fit—not accurate prediction of exact
future volatility surprise.

## 6. Inner-selected hyperparameters

| Outer fold | Ridge alpha | HGB `(learning_rate, leaves, min_leaf, l2)` |
| --- | ---: | --- |
| 2017–2018 | 0.1 | `(0.03, 15, 50, 1.0)` |
| 2019–2020 | 1.0 | `(0.05, 15, 20, 0.0)` |
| 2021–2022 | 10.0 | `(0.03, 15, 50, 0.0)` |
| 2023 | 100.0 | `(0.03, 15, 50, 0.0)` |
| 2024 | 10.0 | `(0.03, 15, 50, 0.0)` |
| 2025 | 100.0 | `(0.03, 15, 50, 0.0)` |
| 2026 partial | 100.0 | `(0.03, 15, 20, 1.0)` |

HGB used `max_iter=200`, `early_stopping=false` and seed `20260827` throughout. Parameter variation
across outer histories is expected from genuine nested temporal selection and was not adjusted
after viewing outer results.

## 7. Limitations carried forward

- F3 found temporal exclusion concentration in 2012, 2013, 2016, 2017, 2019 and the 2017–2018
  outer block. F5 does not erase that coverage limitation.
- The ten-ticker universe and available provider history constrain generalization.
- Retrospective folds estimate historical OOS behavior; prospective external validity remains
  future work.
- F5 does not yet establish decile monotonicity, top-decile lift, ticker/regime robustness or
  bootstrap uncertainty. Those are F6 questions.
- These scores forecast relative volatility surprise, not direction, return or investment value.

## 8. Stop boundary

F5 is complete. The next minimum executable unit, only after user review/approval, is
**F6 — Ranking & Robustness Analysis** using the immutable OOF predictions above. F6 may diagnose
the frozen predictions but must not retune candidates or rewrite F5 outer results.
