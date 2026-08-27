# M9 Conditional Risk / Simpson Analysis — Final Raw-Free Result

## Decision

M9 is complete. It read the one immutable 3,647-row M7 prediction set and the immutable M8 regime
definition without rerunning either milestone, refitting a classifier, changing predictions or
changing the historical 0.10 threshold.

The evidence supports the cautious framing **stock-normalized volatility surprise risk model**.
The model contains information about conditional future volatility, but it is not a general
absolute-volatility predictor. The aggregate-versus-regime reversal in all three raw outcomes is
consistent with a **Simpson-type composition effect**; it is not presented as a causal proof or a
definitive statistical paradox.

## Aggregate and regime-standardized comparisons

All values below are predicted HIGH_RISK minus predicted NORMAL means.

| Outcome | Aggregate difference | Common-regime standardized difference | Composition component |
| --- | ---: | ---: | ---: |
| Next absolute log return | -0.00185 | +0.00361 | -0.00546 |
| Next high-low log range | -0.00294 | +0.00439 | -0.00733 |
| Next Parkinson proxy | -0.00177 | +0.00264 | -0.00440 |
| Normalized continuous outcome | +0.32146 | +0.33604 | -0.01458 |
| Additive absolute-return surprise vs prior volatility | +0.00834 | +0.00827 | +0.00007 |

For every raw outcome, the aggregate difference is negative while LOW, MIDDLE and HIGH historical
stock-volatility regimes all have positive differences. Reweighting both predicted groups to the
same pooled regime proportions makes all three raw differences positive. The negative composition
component is larger than the positive within-regime component and creates the aggregate reversal.

## Composition evidence

Predicted HIGH_RISK rows contain 32.9% LOW, 24.4% MIDDLE and 42.7% HIGH stock-volatility regimes.
Predicted NORMAL rows contain 7.7% LOW, 16.6% MIDDLE and 75.6% HIGH. The regime-composition total
variation distance is 0.329. Ticker and quarter total variation distances are 0.251 and 0.184,
showing additional—but smaller—composition differences.

Ticker evidence remains heterogeneous. HIGH_RISK has higher next absolute return for 6/10 tickers
and higher range/Parkinson proxy for 5/10. In contrast, normalized outcome and additive surprise
differences are positive for all 10 sufficiently sampled tickers. Therefore ticker evidence does
not justify a universal raw-volatility claim, while it is consistent with a relative-surprise
interpretation.

## Conditional regression diagnostic

The predeclared OLS/HC3 diagnostic controls for prior 20-session stock volatility, ticker fixed
effects and calendar-quarter fixed effects. The frozen predicted HIGH_RISK indicator coefficients
are positive:

| Outcome | Coefficient | HC3 95% interval |
| --- | ---: | ---: |
| Next absolute log return | +0.00478 | +0.00331 to +0.00626 |
| Next high-low log range | +0.00448 | +0.00328 to +0.00569 |
| Next Parkinson proxy | +0.00269 | +0.00197 to +0.00341 |
| Normalized continuous outcome | +0.27971 | +0.21038 to +0.34904 |

These regressions are descriptive diagnostics. HC3 addresses heteroskedasticity but not every form
of serial dependence, provider revision, omitted-variable bias or causal identification. P-values
and intervals are not used for classifier, feature or threshold selection.

## Integrity

- M7 evaluation SHA-256:
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`
- M8 analysis SHA-256:
  `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`
- M9 analysis SHA-256:
  `5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2`
- M9 config SHA-256:
  `3da50e95c4497a90731fb93a160af10b758e7e3e4e300f43c4a2d86ae8dce51a`
- Historical threshold: `0.10`
- M7/M8 rerun, model refit, prediction mutation, threshold change or classifier feedback: `false`
- Raw rows, credentials or private holdings in the public report: `false`

M10 may now reconstruct M6 development-only walk-forward OOF predictions and run the already
frozen operating-point rules. M7/M8/M9 outcomes remain forbidden threshold-selection inputs.
