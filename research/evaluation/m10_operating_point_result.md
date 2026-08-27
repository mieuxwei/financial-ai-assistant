# M10 Operating-Point Calibration Study — Development-Only Result

## Decision

M10 is complete at the development-policy stage. It deterministically reconstructed the frozen M6
Logistic walk-forward OOF predictions and prequential Platt calibration, then applied only the
predeclared 0.01–0.50 grid and Screening/Balanced/Precision rules. It did not call M7, use any
M7/M8/M9 label or outcome, refit the M7 final candidate, or replace the historical 0.10 threshold.

All three selected policies are **development-only and unvalidated on a new holdout**. They may
enter M11/M12 comparisons but may not be exposed as production or user-selectable modes.

## Reconstructed development evidence

- Selection rows: 13,550 across M6 folds 2019–2024; fold 2017–2018 is calibration history only.
- HIGH_RISK rows: 1,378.
- Latest target session: 2024-12-31.
- Five Logistic fold-state SHA-256 values exactly match the M6 report.
- Four prequential Platt coefficients/intercepts exactly match the M6 report.
- Reproduced pooled Platt Brier: 0.08854; PR-AUC: 0.18422; ROC-AUC: 0.65663.
- Sealed-test rows used: zero.

## Operating-point comparison

Alert rate is the fraction of ticker-session prediction rows classified HIGH_RISK. The final column
expresses the same rate per 252 ticker-session predictions, not per investor or calendar year.

| Policy | Threshold | Precision | Recall | Specificity | F1 | MCC | Alert rate | Alerts / 252 rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical M7 configuration | 0.10 | 0.155 | 0.586 | 0.639 | 0.245 | 0.139 | 38.4% | 96.8 |
| Screening candidate | 0.09 | 0.144 | 0.681 | 0.541 | 0.238 | 0.134 | 48.2% | 121.4 |
| Balanced candidate | 0.11 | 0.170 | 0.499 | 0.724 | 0.254 | 0.148 | 29.9% | 75.2 |
| Precision candidate | 0.13 | 0.193 | 0.325 | 0.846 | 0.242 | 0.137 | 17.1% | 43.2 |

Screening trades substantially more false alarms for higher sensitivity. Balanced has the highest
development MCC and F1 of the four displayed policies, but its recall is just below 0.50. Precision
reduces alerts and raises precision, yet 0.193 is not high enough to justify a `high-confidence`
product claim. The names describe frozen development objectives, not validated UX quality.

## Calibration evidence

The two populated low-probability bins are reasonably aligned: `[0.0, 0.1)` has mean probability
0.0655 versus observed rate 0.0684, and `[0.1, 0.2)` has 0.1295 versus 0.1450. Bins above 0.30
contain only 99 total rows and are too sparse for strong calibration conclusions. Threshold policy
changes classification/alert frequency; it does not recalibrate probabilities.

## Integrity

- Development OOF dataset SHA-256:
  `975c00f6fd835a6415b0120ab435c1c36bc0d333dbf7b2c95b1f3e8e5d73a4ed`
- M10 analysis SHA-256:
  `21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c`
- M10 canonical config SHA-256:
  `f068a3c2803cf2b7d6b25cf59147ddc3decb3a1a91d1330095d83b8430c73f18`
- Historical threshold replaced: `false`.
- M7 final candidate refit: `false`.
- M7/M8/M9 labels or outcomes used: `false`.
- Result scope: `DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT`.

M11 may now compare the historical 0.10 policy, these global candidates and one frozen model with
regime-aware thresholds using the same development OOF evidence. M11 must not introduce separate
models or read M7/M8/M9 outcomes.
