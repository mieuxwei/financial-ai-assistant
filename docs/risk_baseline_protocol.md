# M4 Leakage-Safe Risk Baseline Protocol

Experiment version: `risk-baselines-v1`  
Configuration: `research/configs/risk_baselines.v1.json`

## Purpose and boundary

M4 establishes three fixed comparisons for next-session `HIGH_RISK` prediction:

1. training historical-risk rate as a constant probability;
2. previous-period risk-label persistence;
3. `StandardScaler` followed by class-balanced Logistic Regression.

Only the 23 M3 market features are used. There is no NLP, portfolio, private-user, news, LLM,
imputation, resampling, feature selection, hyperparameter search, or threshold search. The decision
threshold is fixed at 0.5. Validation labels are opened for M4 evaluation only; sealed-test
features, labels, outcomes and performance remain unopened.

## Train-only fitting

The scaler mean and population standard deviation are fit on training rows and then applied to
validation. Logistic Regression uses `C=1`, `solver=lbfgs`, `l1_ratio=0`, balanced class weights,
`max_iter=2000`, tolerance `1e-6`, and random state `20260827`. Class weights are therefore derived
only from training labels. This follows scikit-learn's estimator/pipeline leakage boundary: fit
preprocessing on training data, then transform later data.

The immutable model JSON stores feature order, training-row hash, scaler state, coefficient,
intercept, library versions, full lineage and a learned-state hash. It does not store validation
rows or predictions. A mutation test changes validation features and labels and proves the learned
state is unchanged while evaluation output changes.

## Naive baselines

The historical-risk baseline emits the training HIGH_RISK prevalence for every validation row.
The persistence baseline uses a ticker's immediately preceding row only when that row's declared
`target_session` exactly equals the current `feature_session`. This makes the preceding label
observable at the current post-close cutoff. Otherwise it falls back to training prevalence; it
never bridges a missing session or looks ahead.

## Metrics and interpretation

M4 reports Balanced Accuracy, HIGH_RISK precision/recall/F1, Macro-F1, MCC, PR-AUC, ROC-AUC,
Brier score, specificity, false-negative count/rate, confusion matrix and supplemental accuracy.
Ten fixed uniform probability bins report mean prediction and observed rate. Empty bins remain
explicit.

Balanced class weights improve minority-class sensitivity but alter the fitted probability scale.
Therefore the Logistic output is an uncalibrated baseline probability, not a final calibrated risk
estimate. M4 performs no model selection. Tree-model comparison, temporal folds, calibration and
candidate selection belong to M5–M6.

## Safety and sealing

The runner verifies the complete M3 hash, exact train/validation split set, chronological ordering,
fixed feature names, finite values, unique identities and valid labels. It rejects any sealed or
unknown split, fitted M3 preprocessing, pre-trained M3 state, hash mismatch, altered feature
contract or non-0.5 decision threshold. Generated model and machine report paths must remain under
Git-ignored `.tools/` or `artifacts/` directories.

`HIGH_RISK` is an automatically generated research label. It is not a price-direction forecast,
buy/sell recommendation, or guarantee of future performance.
