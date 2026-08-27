# M11 Regime-Aware Threshold Study — Development-Only Result

## Decision

M11 is complete at the development-policy stage. Using the unchanged M10 Logistic/Platt OOF
probabilities, the frozen search selected LOW `0.12`, MIDDLE `0.10` and HIGH `0.08`. The policy
substantially reduces cross-regime recall and specificity dispersion, but gives up overall MCC and
F1 relative to the strongest displayed global policies. It is therefore a stability-oriented
candidate, not a general performance improvement or a production policy.

The result is **development-only and unvalidated on a new holdout**. Historical threshold `0.10`
remains unchanged. M12 is unavailable and unopened.

## Leakage-safe regime construction

- Input: the immutable 13,550-row M10 development OOF dataset through 2024-12-31.
- Regime feature: trailing 20-session stock volatility known after close at session `t`.
- Each fold's tertiles were fit only on expanding training rows whose targets preceded that fold's
  evaluation start.
- OOF regime counts were LOW 4,816, MIDDLE 4,407 and HIGH 4,327; positive counts were 607, 443 and
  328 respectively.
- Prospective cutoffs fitted on all 28,690 pre-test rows through 2024 are `0.010232443346` and
  `0.015485021568`. They were not used to reassign historical development rows.
- No separate regime model was trained. No M7/M8/M9 label or outcome was used.

## Frozen search result

The 0.01–0.50 grid yields 125,000 threshold triplets. Seventy-three satisfied all frozen overall,
per-regime and sample-size constraints. The primary rule minimized the worse of cross-regime
recall and specificity ranges; MCC and the declared tie-breakers were secondary.

| Policy | Threshold(s) | Precision | Recall | Specificity | F1 | MCC | Recall range | Specificity range | Alert rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical global | 0.10 | 0.155 | 0.586 | 0.639 | 0.245 | 0.139 | 0.405 | 0.426 | 38.4% |
| M10 Screening | 0.09 | 0.144 | 0.681 | 0.541 | 0.238 | 0.134 | 0.429 | 0.520 | 48.2% |
| M10 Balanced | 0.11 | 0.170 | 0.499 | 0.724 | 0.254 | 0.148 | 0.342 | 0.320 | 29.9% |
| M10 Precision | 0.13 | 0.193 | 0.325 | 0.846 | 0.242 | 0.137 | 0.162 | 0.151 | 17.1% |
| M11 regime-aware | L 0.12 / M 0.10 / H 0.08 | 0.158 | 0.510 | 0.693 | 0.242 | 0.131 | 0.034 | 0.043 | 32.8% |

For the selected policy, regime recalls are LOW 0.529, MIDDLE 0.494 and HIGH 0.497; specificities
are 0.670, 0.697 and 0.713. The lower HIGH-regime threshold and higher LOW-regime threshold correct
the large sensitivity/specificity imbalance seen with one global cutoff. However, overall MCC is
below historical 0.10 and M10 Balanced, and precision remains only 0.158. The evidence supports a
development hypothesis that regime-aware thresholds improve operating stability, not that they
improve discrimination, calibration, investment outcomes or user value.

## Integrity

- Development OOF SHA-256:
  `975c00f6fd835a6415b0120ab435c1c36bc0d333dbf7b2c95b1f3e8e5d73a4ed`
- M11 canonical config SHA-256:
  `d9678cc60b1bd2847a2105b02738122c9230237ca783557531f8b84e3a3c3922`
- M11 analysis SHA-256:
  `76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88`
- Sealed-test rows used: zero.
- M7 rerun, final-candidate refit and separate-regime-model training: `false`.
- Result scope: `DEVELOPMENT_ONLY_UNVALIDATED_ON_NEW_HOLDOUT`.

M12 must freeze this policy and the comparator policies before any genuinely new outcome is
available. It cannot be completed now because the prospective minimum of 126 exchange sessions,
1,000 eligible rows and 50 HIGH_RISK outcomes has not accumulated. M13 remains optional and may not
start without explicit authorization plus independent M12 evidence.

