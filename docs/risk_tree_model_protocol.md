# M5 Fixed Tree-Model Comparison Protocol

Experiment version: `risk-tree-models-v1`  
Configuration: `research/configs/risk_tree_models.v1.json`

## Purpose and fair-comparison boundary

M5 compares two nonlinear candidates against the already-frozen M4 baselines:

- Random Forest;
- HistGradientBoosting.

Both use the identical M3 23-feature matrix, 23,890 training rows, 4,800 validation rows, M2 binary
target, and fixed 0.5 decision threshold. There is no imputation, scaling, resampling, feature
selection, NLP input, hyperparameter search or threshold search. Validation is used only for
aggregate evaluation and permutation importance. Sealed-test features, labels, outcomes and
performance remain unopened.

## Frozen candidates

Random Forest uses 400 trees, log-loss splits, maximum depth 10, minimum split/leaf sizes 40/20,
square-root feature sampling, bootstrap sampling and balanced-subsample class weights. Its accepted
configuration is single-threaded with seed `20260827`.

HistGradientBoosting uses log loss, learning rate 0.05, 250 iterations, at most 31 leaves and depth
6, minimum leaf size 20, L2 regularization 1.0, all features per split, 255 bins and balanced class
weights. Internal early stopping is disabled: it cannot silently reserve or inspect a later subset
of the training period. Its seed is `20260827`.

Parameters were declared before the accepted M5 execution and are not changed in response to
validation performance. M6, not M5, owns temporal candidate and calibration selection.

## Importance and resource evidence

For both models, permutation importance independently shuffles each validation feature three times
with a fixed seed and measures mean decrease in PR-AUC. It is model-agnostic evaluation evidence,
not a training input and not a feature-selection instruction. Correlated features can divide or
mask importance, so rankings are descriptive rather than causal.

The machine report records wall-clock fit, validation inference and permutation-importance time,
plus row/feature counts. Timing is environment-specific and excluded from the immutable evaluation
manifest. Models are deliberately not pickled; the immutable config, dataset hash, training hash,
training-probability commitment, library versions and learned-state hash define reproducible M5
evidence without introducing unsafe deserialization artifacts.

## Determinism correction

The initial fixed-seed Random Forest used parallel workers. Validation metrics and importance were
stable, but repeated training-probability SHA-256 commitments differed because parallel floating-
point aggregation was not byte-identical. The immutable writer rejected overwrite. Both diagnostic
manifests and reports remain in ignored local storage as failure evidence.

The accepted config sets Random Forest `n_jobs=1`. Two consecutive full executions then produced an
identical immutable manifest. This correction changes execution determinism only; it was not chosen
to improve validation metrics.

## Metrics, leakage and safety

M5 reports the exact M4 metric set: HIGH_RISK precision/recall/F1, Balanced Accuracy, Macro-F1,
MCC, PR-AUC, ROC-AUC, Brier score, specificity, false negatives, confusion matrix and ten uniform
calibration bins. The runner reuses the M4 hash, split, chronology, identity, label and finite-value
checks. A validation-mutation test proves both fitted tree-state hashes remain unchanged while
validation metrics change. Any sealed split, altered hash, early stopping, threshold change or
feature-contract change is rejected.

`HIGH_RISK` remains an automatically generated abnormal-volatility research proxy. It is not a
direction forecast, investment recommendation or guarantee.
