# M6 Temporal Validation and Candidate Freeze Protocol

Protocol version: `risk-temporal-validation-v1`  
Configuration: `research/configs/risk_temporal_validation.v1.json`

## Expanding-window contract

M6 evaluates the frozen M4/M5 candidates in five ordered folds:

| Fold | Training available through | Evaluation period |
|---|---|---|
| `wf_2017_2018` | 2016-12-31 | 2017–2018 |
| `wf_2019_2020` | 2018-12-31 | 2019–2020 |
| `wf_2021_2022` | 2020-12-31 | 2021–2022 |
| `wf_2023` | 2022-12-31 | 2023 |
| `wf_2024` | 2023-12-31 | 2024 |

A training row is admitted only when its feature session is at or before `train_end` and its
declared next-session target finishes before `evaluation_start`. This target-overlap purge prevents
the last training label from reading the first evaluation session. The target horizon is one
session, so additional post-evaluation embargo is zero. Each Logistic scaler and class weighting,
and each tree class weighting, is fit again from that fold's training rows only.

## Model selection

The candidate set and parameters are exactly hash-bound to M4/M5. The primary selection score is
mean fold PR-AUC. Ties use mean fold MCC, then lower mean Brier, then the predeclared simpler-model
order. No feature, parameter or probability threshold is changed before this comparison.

This rule selected Logistic Regression. Selection is based on all five pre-test folds and cannot be
revisited after M7 opens the sealed test.

## Prequential calibration

For fold 2 onward, Platt calibration is fit on the raw out-of-fold probabilities and labels from
strictly earlier folds, then applied to the current fold. Fold 1 is calibration history only and is
excluded from calibration/threshold comparison because no earlier OOF fold exists. Platt receives
the clipped logit of raw probability, uses no class weighting, and must have a positive coefficient.

Identity versus Platt is selected by pooled Brier score over folds 2–5. Platt reduced Brier from
0.2244 to 0.0885 and was accepted. A 0.5 cutoff on prevalence-calibrated probabilities would miss
almost every HIGH_RISK row; this is why M6 separately selects a decision threshold rather than
mistaking calibration for classification.

## Threshold selection

The frozen grid is 0.05 through 0.95 in 0.05 increments. Eligible thresholds must achieve pooled
prequential HIGH_RISK recall of at least 0.50. Among eligible values, maximum MCC wins; ties prefer
higher precision, closeness to 0.5, then the lower threshold. Threshold 0.10 was selected with:

- HIGH_RISK recall 0.5856;
- precision 0.1551;
- MCC 0.1394;
- PR-AUC 0.1842;
- ROC-AUC 0.6566;
- Brier 0.0885.

## Final pre-test recipe

After selection, Logistic Regression and its StandardScaler are fit on all 28,690 available
2011–2024 rows. The final Platt calibrator is fit on all 16,970 walk-forward OOF predictions, never
on in-sample final-model predictions. Model/scaler state, calibrator coefficient/intercept,
threshold, upstream hashes and final-fit hashes are frozen in an immutable manifest. Models are not
pickled; M7 must deterministically reconstruct the exact recipe from trusted code and verify state
hashes before evaluation.

## Sealed-test boundary

M6 rejects any feature session on or after 2025-01-01. Its manifest records:

- `candidate_recipe_frozen = true`;
- `sealed_test_features_or_outcomes_opened = false`;
- `sealed_test_evaluations = 0`.

M7 may open the 2025-01-01–2026-08-26 test only after matching candidate manifest SHA-256
`951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`. Test results cannot change
the model, scaler, calibrator, threshold, features or target. The risk output remains research-only
and is not investment advice.
