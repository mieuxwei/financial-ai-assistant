# Post-M8 Risk Research Extension Protocol

Protocol version: `post-m8-risk-extension-v1`  
Status: **M9–M10 complete; M11–M12 not executed**

## 1. Historical evidence boundary

M7 and M8 are immutable historical evidence. The one M7 evaluation contains 3,647 predictions,
uses the historical threshold 0.10 and has evaluation SHA-256
`4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`. M8 analysis SHA-256 is
`c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`.

M7/M8 rows may be read only for the M9 conditional diagnostic. They may never be inputs to model,
calibrator, regime-cutoff or decision-threshold selection. The 0.10 operating point remains the
historical M7 configuration; post-M8 policies are new development hypotheses and cannot replace it
until an independently frozen prospective holdout validates them.

## 2. Research questions

- **RQ-A — Conditional interpretation:** does the frozen model identify high absolute future
  volatility, or volatility unusually high relative to the stock's own historical context?
- **RQ-B — Operating-point calibration:** can policies selected only from pre-test development
  predictions offer useful product-specific precision/recall trade-offs?
- **RQ-C — Regime-aware policy:** can one frozen model plus time-observable regime thresholds reduce
  sensitivity/specificity instability relative to a global threshold?
- **RQ-D — Model complexity:** only if threshold policies remain insufficient, is there enough new
  validated evidence to justify regime-specific modeling?

## 3. M9 — Conditional Risk / Simpson Analysis

M9 is analysis-only. It retains the existing M7 predictions and threshold. Aggregate, fixed
stock-volatility-regime, ticker and calendar-quarter comparisons cover raw next-session absolute
return, high-low range, Parkinson proxy and the normalized continuous outcome. Regime cutoffs are
the pre-test-only tertiles already frozen for M8. Composition tables compare how predicted groups
are distributed across regimes, tickers and time periods.

An optional predeclared OLS/HC3 diagnostic may regress each outcome on the frozen predicted-risk
indicator, prior 20-session stock volatility, ticker fixed effects and calendar-quarter fixed
effects. It is explanatory only and cannot feed the classifier or later threshold search. M9 must
separately conclude on aggregate raw separation, within-regime separation and normalized surprise
separation. The preferred term is `Simpson-type composition effect`; definitive causal or
`Simpson's paradox` language requires stronger statistical support.

Configuration: `research/configs/post_m8_conditional_risk.v1.json`.

Implementation result: M9 found a complete aggregate/within-regime direction reversal for all
three raw volatility outcomes. Common-regime standardization and the predeclared OLS/HC3 diagnostic
support a conditional relative-surprise interpretation, while ticker raw outcomes remain mixed.
See `research/evaluation/m9_conditional_risk_result.md`. This evidence does not alter M7/M8 or tune
any later policy.

## 4. M10 — Operating-Point Calibration Study

M10 may use only deterministic reconstruction of the M6 2017–2024 walk-forward OOF development
predictions. M6 did not persist row-level OOF predictions, so a future implementation must rebuild
them from the frozen M6 folds/configuration and first demonstrate matching aggregate lineage. This
reconstruction may fit the historical fold models required to reproduce development OOF evidence;
it may not refit or alter the frozen M7 final candidate.

The search grid and objectives are frozen before search:

- Screening: maximize recall subject to specificity at least 0.50 and precision at least 0.12.
- Balanced: maximize MCC subject to recall at least 0.40 and specificity at least 0.50.
- Precision: maximize precision subject to recall at least 0.30 and specificity at least 0.70.
- Grid: 0.01 through 0.50 inclusive in exact 0.01 increments, with fixed tie-breakers in config.

If a mode has no eligible threshold, its outcome is `INCONCLUSIVE_NO_POLICY_SELECTED`. All M10
results remain development-only. M7/M8 labels and metrics are forbidden selection inputs.

Configuration: `research/configs/post_m8_operating_points.v1.json`.

Implementation result: exact M6 development reconstruction produced 13,550 selection rows through
2024. Frozen rules selected 0.09 Screening, 0.11 Balanced and 0.13 Precision candidates. All remain
development-only; none replaces historical 0.10 or enables product modes. See
`research/evaluation/m10_operating_point_result.md`.

## 5. M11 — Regime-Aware Threshold Study

M11 keeps one frozen Logistic/Platt model and studies three decision thresholds. The regime feature
is `volatility_log_return_20`, calculated from 20 sessions ending at `t` and known post-close at
prediction time. During walk-forward development, tertile cutoffs are fitted from each fold's
expanding training history only. The final prospective cutoff may be fitted through 2024 only.
Neither `t+1` outcome nor future volatility may define the regime.

Candidate policies must satisfy the predeclared overall/per-regime recall, specificity and sample
constraints. The primary rule minimizes the larger of recall-range and specificity-range across
regimes; overall MCC is secondary. It compares historical 0.10, eligible M10 global policies and
the regime-aware policy. No separate regime model is allowed in M11.

Configuration: `research/configs/post_m8_regime_thresholds.v1.json`.

## 6. M12 — Prospective / New-Holdout Validation

The existing M7 interval cannot validate post-M8 policies. M12 therefore begins with the first
exchange session after 2026-08-26 and remains unavailable/unopened in this planning milestone. It
requires at least 126 completed exchange sessions, 1,000 eligible rows and 50 HIGH_RISK outcomes;
if evidence remains smaller, the conclusion must say `PROSPECTIVE_EXPLORATORY_VALIDATION`.

Before any outcome/label access, an immutable policy manifest must freeze the base model, feature
and label protocols, original 0.10 policy, selected M10 global policies, M11 regime policy and
cutoffs, plus all evaluation metrics. All policies run on the exact same holdout. Subgroup results
are reported but never used for another tuning round. The holdout is currently inaccessible to
tuning code and has not been materialized.

Configuration: `research/configs/post_m8_prospective_validation.v1.json`.

## 7. M13 — Optional Regime-Specific Modeling

M13 must not start automatically. It requires explicit authorization and a complexity
justification based on M11 development evidence plus M12 new-holdout evidence. Any proposal must
address reduced samples, overfitting, regime-transition instability, selection multiplicity,
deployment and explanation cost. Separate classifiers, interaction models and mixture-of-experts
gating remain optional extensions rather than completion requirements.

## 8. Product interpretation

Until M9 finishes, the safe name remains `next-session abnormal volatility risk model`. Do not
claim an absolute-volatility predictor or adopt `stock-normalized volatility surprise risk model`
as a final conclusion. Screening, Balanced and High-Confidence UX modes are design candidates only;
none may be exposed until M12 independently validates its frozen policy.

## 9. Automated boundary protection

`research/evaluation/post_m8_research_boundaries.py` and its tests assert frozen M7/M8 hashes,
prediction count and threshold; M9 analysis-only behavior; development-only M10/M11 selection;
time-observable lagged regime state; prohibition of separate M11 models; and an inaccessible,
unopened M12 holdout with a mandatory pre-opening policy manifest.
