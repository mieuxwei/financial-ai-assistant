# F4 Regression Candidate Implementation Result

Status: **COMPLETE — IMPLEMENTATION VERIFIED, HISTORICAL EVALUATION NOT RUN**

Experiment version: `final-regression-candidates-v1`

F4 config SHA-256:
`88ff58b4510cec94c0f0b5a1c895cad3bafc126bf61048d01facdfb1dbfae726`

Frozen F1 config SHA-256:
`4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66`

## Implemented candidates

| Model | Candidate settings | F4 behavior |
| --- | ---: | --- |
| Normalized-move persistence | 1 | No fitted parameter; uses `abs(return_log_1) / max(volatility20, 1e-8)` |
| Ridge Regression | 4 | Training-only StandardScaler; alpha 0.1/1/10/100 |
| HistGradientBoostingRegressor | 16 | Fixed F1 grid; squared-error loss; internal early stopping disabled |

Total parameterized candidates: 21. This is the frozen search space for the later inner temporal
selection procedure, not 21 final models.

## Target and prediction contract

- Target: `next_session_stock_normalized_abs_log_return_v1`.
- Trainable candidates fit `log1p(target)`.
- Predictions return to the original scale with `max(0, expm1(prediction))`.
- All model inputs use the fixed 23-feature order from `risk-features-v1`.
- Persistence predictions are already on the original target scale.
- No clipping or target normalization parameter is learned globally.

## Temporal safety

Every fit requires an explicit `TemporalFitContext` containing training start/end and the next
validation/evaluation start. The runner rejects:

- feature sessions outside the declared training history;
- training targets that reach or cross the validation/evaluation boundary;
- duplicate ticker/session rows;
- target/future fields in predictors;
- non-finite features or targets;
- hyperparameters outside the frozen F1 grids.

Ridge fits its scaler only on the supplied training rows. HGB receives the same unscaled features
and has `early_stopping=False`, so it cannot silently carve out an internal validation fraction.

## Reproducibility contract

Each fit creates an in-memory candidate plus a JSON-safe fit manifest containing:

- exact F1/F4/dataset hashes;
- temporal fit boundary;
- ordered training-row hash;
- model name and hyperparameters;
- software versions;
- Ridge scaler/coefficients or HGB deterministic training-prediction fingerprint;
- explicit false flags for validation fitting, hyperparameter selection and persisted final model.

Repeated synthetic Ridge and HGB fits produced identical manifests and predictions. F4 does not
persist a production model; that belongs to F7 after F5/F6 evidence and frozen selection.

## Boundary and result

The machine contract report confirms:

- validation/outer rows used for fitting: false;
- hyperparameter selection performed: false;
- historical outer evaluation run: false;
- final model artifact persisted: false;
- historical models trained during contract verification: false.

No MAE, RMSE, R², Spearman, lift or winner is reported in F4. Those belong to F5/F6. F5 has not
started.
