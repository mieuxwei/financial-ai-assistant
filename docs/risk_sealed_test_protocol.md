# M7 One-Time Sealed-Test Protocol

Protocol version: `risk-sealed-test-v1`  
Configuration: `research/configs/risk_sealed_test.v1.json`

## Authorization and immutable boundary

The user explicitly approved the only M7 evaluation after M6 commit `2c2cb81` was present on
`origin/main`. Preflight verified candidate manifest SHA-256
`951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`, upstream M1–M5 hashes,
frozen Logistic/Platt/0.10 selection and `sealed_test_evaluations = 0`.

M7 creates three ignored local records:

1. opening intent, written before loading test market rows;
2. immutable row-level evaluation;
3. completion record linking manifest, opening, evaluation and aggregate report hashes.

The runner refuses execution whenever any of these records already exists. A crash after opening
would still consume the single evaluation; recovery could document the failure but could not claim
a fresh sealed test. The completed project now has evaluation sequence 1 and repeats are forbidden.

## Frozen reconstruction

The evaluator rebuilds the 2011–2024 StandardScaler and Logistic Regression from the immutable M3
pre-test rows. Scaler state, coefficients, intercept, training probabilities and hashes must exactly
match the M6 candidate before test predictions are accepted. It applies the frozen Platt coefficient
and intercept, then the frozen 0.10 threshold. No model, calibration, feature or threshold selection
is allowed.

M2's ordinary builder continues to exclude test. A separate explicit M7 path applies the existing
train-only threshold to test outcomes and calculates the same 23 M3 features. Each row requires an
exact next benchmark session and complete 35-session stock/TAIEX history. Missing rows abstain; no
gap is filled.

## Test and reporting contract

- Period: 2025-01-01–2026-08-26.
- Eligible rows: 3,647 across the frozen ten-ticker universe.
- Actual HIGH_RISK rows: 390 (10.69%).
- Detailed features, outcomes and probabilities: ignored local evaluation only.
- Public evidence: aggregate metrics, calibration bins, confusion matrix, exclusions and grouped
  realized outcomes.

Test results cannot be used to retrain, recalibrate, change the cutoff, remove features or choose a
different model. M8 may only read the existing immutable evaluation for error/robustness analysis.

## Interpretation boundary

The target is next-session absolute return divided by trailing volatility known at `t`. M7 shows
predicted HIGH_RISK has higher normalized outcome but not higher raw absolute return or high-low
range. The correct claim is therefore modest separation of normalized surprise risk, not general
absolute volatility, direction, profitability or investment advice.
