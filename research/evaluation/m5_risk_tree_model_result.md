# M5 Tree Models — Raw-Free Validation Result

Evaluation date: 2026-08-27  
Experiment: `risk-tree-models-v1`  
Result: **PASS — negative incremental comparison preserved**

## Data and boundary

- Training rows: 23,890.
- Validation rows: 4,800, including 488 HIGH_RISK rows.
- Feature count: 23.
- Decision threshold: fixed 0.5.
- Validation used for fitting, early stopping or threshold tuning: **false**.
- Hyperparameter or feature selection performed: **false**.
- Validation predictions persisted: **false**.
- Sealed-test features, outcomes or performance opened: **false**.

## Aggregate validation metrics

| Model | Balanced accuracy | Precision | HIGH_RISK recall | F1 | Macro-F1 | MCC | PR-AUC | ROC-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M4 Logistic Regression | 0.599 | 0.146 | 0.582 | 0.234 | 0.487 | 0.122 | 0.172 | 0.645 | 0.224 |
| Random Forest | 0.566 | 0.165 | 0.307 | 0.215 | 0.540 | 0.101 | 0.156 | 0.613 | 0.185 |
| HistGradientBoosting | 0.559 | 0.148 | 0.338 | 0.206 | 0.523 | 0.084 | 0.151 | 0.614 | 0.177 |

Tree-model confusion matrices (`NORMAL` negative, `HIGH_RISK` positive):

| Model | TN | FP | FN | TP | FNR |
|---|---:|---:|---:|---:|---:|
| Random Forest | 3,552 | 760 | 338 | 150 | 0.693 |
| HistGradientBoosting | 3,361 | 951 | 323 | 165 | 0.662 |

Both tree models reduce false positives and Brier loss relative to the class-balanced Logistic
baseline, but miss substantially more HIGH_RISK rows and have lower PR-AUC, ROC-AUC and MCC. Neither
tree model dominates Logistic. M5 therefore records a negative incremental result and does not
select a final candidate. Temporal stability and calibrated trade-offs belong to M6.

## Validation permutation importance

Top five mean PR-AUC decreases:

| Rank | Random Forest | Mean decrease | HistGradientBoosting | Mean decrease |
|---:|---|---:|---|---:|
| 1 | `volatility_log_return_20` | 0.0274 | `volatility_log_return_20` | 0.0386 |
| 2 | `benchmark_drawdown_20` | 0.0092 | `rsi_14` | 0.0079 |
| 3 | `volume_zscore_20` | 0.0087 | `return_log_10` | 0.0056 |
| 4 | `rsi_14` | 0.0076 | `volume_zscore_20` | 0.0052 |
| 5 | `close_ma_deviation_5` | 0.0045 | `overnight_gap_log_1` | 0.0051 |

These are descriptive validation importance values, not causal effects or a selected feature set.

## Observed resource cost and reproducibility

On the current local run, single-thread Random Forest fit in about 13.6 seconds and HGB in about
1.9 seconds. Validation inference was below 0.1 seconds for each. Timing is operational evidence,
not a benchmark guaranteed across machines.

- M3 dataset SHA-256:
  `a9898ce18a2497efaa98d22dc5e99f40bae446f175781c3c47bde92972d26bb0`.
- M5 config SHA-256:
  `11d68659f67287b2728501dae70224f51f6af766ab57e29c1492382ed484c691`.
- Training rows SHA-256:
  `06d219fb45ee574a4d215bf1f7a8ffe7d34f09becafb836d42bc31ab2bb30fc5`.
- Random Forest state SHA-256:
  `164c3115fbf543e7665c81597aedc96051680fc724cb4c0b4c8933a25e248590`.
- HistGradientBoosting state SHA-256:
  `6c73a23cbbe2f65aaaad0c42c94eab96d02045413022839c532c1edb8a395cef`.
- Accepted evaluation manifest SHA-256:
  `e21cda5dfd612fa5f84636903b8e5cce2f1449566bf45a403ee7093678f8590f`.

The first parallel Random Forest attempt failed byte-identical reconstruction and was preserved in
ignored local diagnostic files. The accepted single-thread manifest passed two consecutive full
rebuilds. Detailed machine reports and provider-derived rows remain ignored and contain no secrets,
private holdings or personal information.
