# M8 Risk Error Analysis and Robustness — Final Raw-Free Result

## Decision

M8 is complete. It read the existing immutable M7 evaluation of 3,647 rows without rerunning M7,
refitting a model, generating a second prediction set or selecting a different threshold. The M7
evaluation sequence remains exactly one.

The result supports **modest but heterogeneous normalized surprise-risk discrimination**. It does
not support a claim of stable performance across every ticker/quarter, general absolute-volatility
separation, direction prediction, trading profitability or investment utility.

## Overall uncertainty

The frozen M7 point estimates remain recall 0.508, precision 0.180, MCC 0.155, PR-AUC 0.189,
ROC-AUC 0.686 and Brier 0.0926. A 1,000-sample feature-session cluster bootstrap produced these 95%
percentile intervals:

| Metric | Point estimate | 95% interval |
| --- | ---: | ---: |
| HIGH_RISK recall | 0.508 | 0.441–0.576 |
| MCC | 0.155 | 0.109–0.202 |
| PR-AUC | 0.189 | 0.151–0.242 |
| ROC-AUC | 0.686 | 0.650–0.724 |
| Brier score | 0.0926 | 0.0792–0.1067 |

These intervals account for within-session cross-ticker clustering, but not all forms of temporal
dependence, provider revision or future regime change.

## Time and ticker heterogeneity

Quarterly recall ranged from 0.310 in 2026-Q2 to 0.656 in 2025-Q4. The strongest ranking quarter
was 2025-Q2 (PR-AUC 0.332, ROC-AUC 0.802, MCC 0.284); weaker periods include 2025-Q3 (MCC 0.038)
and 2026-Q2 (MCC 0.046). The rebound in 2026-Q3 does not erase this drift evidence.

Ticker recall ranged from 0.326 for 2308 to 0.794 for 2412. High recall can be expensive: 2412 had
27 TP but 174 FP, giving precision 0.134. Conversely, 2330 had the highest ticker precision in this
set at 0.255 but recall only 0.333. No ticker-specific threshold is selected from these results.

## Volatility regimes and errors

Using stock-volatility cutoffs fitted only on the 2011–2024 pre-test data, HIGH-regime recall was
0.383 with specificity 0.822, while LOW-regime recall was 0.811 with specificity 0.377. This
indicates a sensitivity/specificity shift rather than uniformly robust classification. Market
regimes show the same trade-off more mildly: HIGH-market-volatility recall/specificity were
0.468/0.778 versus 0.640/0.479 in the MIDDLE regime. No sealed-test rows fell in the pre-test LOW
market-volatility regime, itself useful distribution-shift evidence.

Overall errors were TN 2,352, FP 905, FN 192 and TP 198. False positives dominate the error count,
while the 192 false negatives mean 49.2% of observed HIGH_RISK sessions were missed. The fixed
0.10 threshold therefore behaves as a risk-screening compromise, not a precise alarm.

## Probability and realized-outcome evidence

Most probabilities were low: 2,544 rows were below 0.10, and 1,012 were in `[0.10, 0.20)`. Their
mean probabilities versus observed HIGH_RISK rates were 0.053 versus 0.075 and 0.133 versus 0.168,
respectively. Buckets above 0.30 contained too few rows for strong calibration claims; no
post-test recalibration is performed.

Predicted HIGH_RISK rows retained higher normalized continuous outcome than NORMAL rows (mean
1.087 versus 0.766; median 0.876 versus 0.574). However, overall raw next-session absolute return,
high-low range and Parkinson proxy were lower by 0.00185, 0.00294 and 0.00177, respectively. The
stock-volatility-stratified comparisons turn positive within every regime, while market-regime
comparisons remain negative. This dependence on conditioning is consistent with composition /
Simpson-type effects and must not be simplified into a general absolute-volatility claim.

## Integrity and next boundary

- M7 evaluation SHA-256:
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`
- M8 analysis SHA-256:
  `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`
- M8 config SHA-256:
  `3cd94110b8ac78d60dff51637b7a1b5b243178ec7568937cbb8716a94bb225d4`
- M7 evaluation sequence: `1`
- M7 rerun performed: `false`
- Model or threshold selection performed: `false`
- Raw rows, secrets or private holdings in the public report: `false`

M9 may now implement the Financial NLP Intelligence layer independently of Track A. M9 must not
use M8 subgroup results to refit or tune the sealed risk candidate, and must preserve unsupported /
abstain behavior for unvalidated Chinese sentiment.
