# F3 Target, Feature and Coverage-Bias Audit Result

Status: **COMPLETE — DATA LIMITATION WITH DETECTED TEMPORAL CONCENTRATION**

Audit version: `final-study-target-feature-coverage-audit-v1`

Coverage-audit config SHA-256:
`4c648450bc46bb48e9d802d2f286b462d0e0faa430c301eb472afebe8ae3a697`

Dataset SHA-256:
`2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`

## Target and row-contract audit

All 32,357 eligible rows passed:

- unique `(ticker, feature_session)` identity;
- exact next benchmark-session target alignment;
- timezone-aware information cutoff on feature session `t`;
- exact 23-feature contract with no target/future fields;
- finite feature and target values;
- `sigma20 > 1e-8` near-zero policy;
- feature, row and dataset SHA-256 verification;
- target reproduction from the original immutable market bars.

The target was recomputed row by row as next-session absolute adjusted-close log return divided by
the population standard deviation of 20 adjusted-close log returns ending at `t`. The complete
target payload, including raw absolute move, range, Parkinson proxy and additive surprise, matched
the frozen builder output.

JSON object key order is not treated as feature order. The fixed model-input order comes from
`risk_features.v1.json`; the audit compares the exact feature-name set and hashes canonical
content. A disk round-trip test protects this distinction.

## Feature availability audit

All features are observable no later than post-close `t`:

| Group | Features | Availability |
| --- | --- | --- |
| Price | returns 1/5/10/20, overnight gap, MA deviations 5/20 | Current/trailing stock bars ending at `t` |
| Volume | log change, z-score20, zero flag | Current/trailing volume ending at `t` |
| Volatility/range | volatility5/20, high-low range, ATR14, Parkinson5 | Current/trailing stock bars ending at `t` |
| Technical | RSI14, MACD12/26, signal9 | Trailing stock bars ending at `t` |
| Market | TAIEX returns1/20, volatility20, stock-minus-market, drawdown20 | Same benchmark session and trailing history ending at `t` |

No global preprocessing, imputation, feature selection or model fitting occurred.

## Predeclared coverage-bias decision rule

A sufficiently sized group is flagged only when its exclusion rate is both:

1. more than 5 percentage points above its axis-wide baseline; and
2. more than 1.5 times its axis-wide baseline.

Minimum group size is 100 candidate rows. Volatility regimes use LOW/MIDDLE/HIGH tertile cutoffs
fitted only from the corresponding outer fold's training rows. Candidates lacking the required
21-bar scale are separately marked `UNAVAILABLE_DUE_TO_COVERAGE_GAP`. No missing-at-random claim is
made.

## Coverage-bias results

### Ticker

Ticker exclusion rates range from 14.68% to 15.59%. No ticker triggered the concentration rule.

### Calendar year

Overall 2011–2026 exclusion rate is 15.49%. Five years triggered the frozen rule:

| Year | Candidates | Exclusion rate | Rate / axis baseline |
| --- | ---: | ---: | ---: |
| 2012 | 2,500 | 24.80% | 1.60× |
| 2013 | 2,460 | 41.06% | 2.65× |
| 2016 | 2,440 | 44.26% | 2.86× |
| 2017 | 2,460 | 43.90% | 2.83× |
| 2019 | 2,420 | 26.86% | 1.73× |

The concentration corresponds to benchmark sessions without the stock bars required by the
strict consecutive-window contract. It is temporal/provider-calendar coverage, not a ticker-
specific exclusion pattern.

### Outer evaluation fold

The outer-evaluation baseline exclusion rate is 12.18%.

| Outer fold | Candidates | Eligible | Exclusion rate | Flagged |
| --- | ---: | ---: | ---: | --- |
| 2017–2018 | 4,930 | 3,420 | 30.63% | Yes, 2.51× baseline |
| 2019–2020 | 4,870 | 4,220 | 13.35% | No |
| 2021–2022 | 4,900 | 4,540 | 7.35% | No |
| 2023 | 2,390 | 2,390 | 0.00% | No |
| 2024 | 2,420 | 2,420 | 0.00% | No |
| 2025 | 2,430 | 2,106 | 13.33% | No |
| 2026 partial | 1,560 | 1,541 | 1.22% | No |

### Training-only volatility regime

Among candidates with a computable `t`-known volatility scale:

| Regime | Candidates | Eligible | Exclusion rate | Flagged |
| --- | ---: | ---: | ---: | --- |
| LOW | 7,950 | 7,346 | 7.60% | No |
| MIDDLE | 6,155 | 5,928 | 3.69% | No |
| HIGH | 7,727 | 7,363 | 4.71% | No |

Another 1,668 evaluation candidates could not receive a regime because the necessary trailing
market bars were missing. This is 7.10% of evaluation candidates and exceeds the predeclared 5%
warning threshold. These candidates were all excluded rather than assigned an inferred regime.

## Final F3 conclusion

The requested full downgrade is **not allowed** because exclusion is abnormally concentrated in
five calendar years and the 2017–2018 outer fold, and the unavailable-regime share exceeds 5%.

Correct classification:

> `DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION`

This is not evidence of target leakage, duplicate contamination, ticker targeting or a broken
feature formula. It is a material temporal data-coverage limitation that must remain visible in
the final report and robustness analysis. F4 may proceed, but F5/F6 must report per-fold sample
counts, avoid sample-size-weighted claims that hide weak-coverage periods, and retain the
2017–2018 limitation explicitly.

No model was trained. F4 has not started.
