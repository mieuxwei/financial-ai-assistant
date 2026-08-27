# M4 Risk Baselines — Raw-Free Validation Result

Evaluation date: 2026-08-27  
Experiment: `risk-baselines-v1`  
Result: **PASS**

## Data and boundary

- Training rows: 23,890.
- Validation rows: 4,800.
- Training HIGH_RISK prevalence: 10.080%.
- Validation HIGH_RISK prevalence: 10.167% (488 rows).
- Decision threshold: fixed 0.5.
- Validation used for fitting or threshold tuning: **false**.
- Validation predictions persisted: **false**.
- Model selection performed: **false**.
- Sealed-test features, outcomes or performance opened: **false**.

All preprocessing, balanced class weights and Logistic Regression parameters were fit from training
rows only. Ten persistence rows lacked an exact previous target-session match and explicitly fell
back to training prevalence.

## Aggregate validation metrics

| Model | Balanced accuracy | Precision | HIGH_RISK recall | F1 | Macro-F1 | MCC | PR-AUC | ROC-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Historical-risk rate | 0.500 | 0.000 | 0.000 | 0.000 | 0.473 | 0.000 | 0.102 | 0.500 | 0.091 |
| Previous-period persistence | 0.526 | 0.148 | 0.148 | 0.148 | 0.526 | 0.051 | 0.108 | 0.525 | 0.173 |
| Logistic Regression | 0.599 | 0.146 | 0.582 | 0.234 | 0.487 | 0.122 | 0.172 | 0.645 | 0.224 |

Confusion matrices (`NORMAL` negative, `HIGH_RISK` positive):

| Model | TN | FP | FN | TP | FNR |
|---|---:|---:|---:|---:|---:|
| Historical-risk rate | 4,312 | 0 | 488 | 0 | 1.000 |
| Previous-period persistence | 3,896 | 416 | 416 | 72 | 0.852 |
| Logistic Regression | 2,655 | 1,657 | 204 | 284 | 0.418 |

The class-balanced Logistic baseline detects more HIGH_RISK rows and improves ranking metrics, but
its fixed threshold also creates many false positives and its Brier score is worse than the
constant-prevalence baseline. This is expected evidence that discrimination and probability
calibration are separate. M4 does not declare a winner or final candidate.

## Reproducibility lineage

- M3 risk-feature dataset SHA-256:
  `a9898ce18a2497efaa98d22dc5e99f40bae446f175781c3c47bde92972d26bb0`.
- M4 config SHA-256:
  `6627f8c920adf32e9e52bc279df25177f20ed1b806922e03221ca95927aef6ff`.
- Training rows SHA-256:
  `06d219fb45ee574a4d215bf1f7a8ffe7d34f09becafb836d42bc31ab2bb30fc5`.
- Learned model state SHA-256:
  `0e5a8d0d9b589a01255353e208106cf3d235e0f0a6ab2ffa813930e56bfe097e`.
- Model artifact SHA-256:
  `7f08686f1f95bcc5bff7a23f1ed071ce97d6755d090752792bfeb93b392efc44`.

The detailed machine report, learned parameters and provider-derived rows remain only in ignored
local paths. This public result contains aggregate validation evidence but no prediction rows,
credentials, private holdings, personal information or sealed-test result.
