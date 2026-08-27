# M8 Risk Error Analysis and Robustness Protocol

## Purpose and immutable boundary

M8 analyzes the one existing M7 sealed-test evaluation. It does not reconstruct the model, produce
new predictions, change the frozen probability threshold, or open the sealed test again. Before
analysis, the runner verifies the SHA-256 chain across the M6 candidate manifest, M7 opening
intent, row-level evaluation, completion record, public aggregate report and pre-test feature
dataset. Every M7 record must retain `evaluation_sequence=1`; repeat evaluation and test-based
model/threshold selection must remain false.

The row-level M7 input and M8 machine outputs stay under Git-ignored `.tools/` and `artifacts/`
paths. Public documentation contains aggregate evidence only.

## Frozen analysis choices

- Decision threshold: the M6/M7 value `0.10`; it is not retuned.
- Ticker and calendar-quarter strata: all observed sealed-test groups.
- Probability buckets: fixed width `[0.0, 0.1), ... [0.9, 1.0]` intervals.
- Stock-volatility regime: tertiles of `volatility_log_return_20` fitted from the 2011–2024
  pre-test feature dataset only.
- Market-volatility regime: tertiles of `benchmark_volatility_log_return_20` fitted from the same
  pre-test-only dataset.
- Full stratum metrics require at least 50 rows, at least five HIGH_RISK rows and both classes.
  Smaller strata remain visible with counts and an insufficient-evidence status.
- Uncertainty: 1,000 deterministic bootstrap samples clustered by feature session, seed 20260827,
  with percentile 95% intervals. Session clustering keeps same-day cross-ticker observations
  together; it does not prove independence or stationarity.

## Outputs

M8 reports recall, precision, F1, Balanced Accuracy, MCC, PR-AUC, ROC-AUC, Brier score, confusion
counts and class prevalence overall and where valid by stratum. It also reports:

- FN/FP/TN/TP distributions by ticker, quarter and volatility regime;
- mean predicted probability versus observed HIGH_RISK rate in fixed probability buckets;
- predicted HIGH_RISK versus NORMAL realized outcomes, both for the normalized primary target and
  raw absolute return, high-low range and Parkinson-volatility proxies.

These are descriptive robustness analyses of a single frozen test evaluation. They are not a new
selection round, causal feature attribution, investment backtest or proof that a subgroup effect
will persist. No subgroup is used to alter the candidate after seeing test results.

## Reproduction

After M7 artifacts and the pre-test feature dataset are present locally:

```bash
python -m jobs.risk_robustness
```

The immutable analysis is written to
`.tools/evaluations/risk-robustness-v1/analysis.json`; the raw-free machine report is written to
`artifacts/m8-risk-robustness-report.json`. Repeating M8 is permitted only as deterministic
verification of the same analysis. Running the M7 sealed-test job is permanently prohibited.
