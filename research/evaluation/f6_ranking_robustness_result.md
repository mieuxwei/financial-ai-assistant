# F6 Ranking & Robustness Analysis Result

Date: 2026-08-28

Status: **COMPLETE — frozen F5 OOF diagnostics; no retuning or final model selection**

## 1. Scope and integrity boundary

F6 analyzed the immutable F5 historical out-of-sample predictions. It did not refit a regressor,
change a hyperparameter, use subgroup evidence for tuning, select the F7 final model, create a
production artifact, rerun M7, modify GAS, deploy, commit or push.

This remains a **retrospective, leakage-aware, hypothesis-informed** study. The findings are ranking
associations in the ten-ticker historical universe, not prospective validation, price-direction
prediction, investment advice or guaranteed future volatility.

## 2. Frozen lineage

| Object | Canonical SHA-256 |
| --- | --- |
| F1 protocol config | `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66` |
| F2 final dataset | `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c` |
| F5 evaluation config | `3ebf45f6054d40724970f1be2f1c0bbf6588cb085b7bafe0196077cc304256af` |
| F5 OOF predictions | `b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7` |
| F6 analysis config | `d860f42a3e47d8b136d93a652be6952de786bcdd5cfd94131b7069967ce9c939` |
| F6 aggregate analysis | `8fd2fdc84f65fb47b6bc87df4b662c4bbd5a9ec8c82d41de4cdd3825b6364e70` |

Every OOF row was rejoined to F2 by ticker/session and verified against `source_row_sha256` and the
stored primary target. All 61,911 predictions mapped exactly to 20,637 unique evaluation rows.

## 3. Frozen analysis method

- Predicted-score deciles were assigned separately inside each model and outer fold.
- `D1` is the lowest predicted-score bucket; `D10` is the highest.
- Ties used prediction descending, feature session ascending and ticker ascending.
- Top-decile/quintile counts used `ceil(q*n)` within each outer fold.
- Stock and market volatility regimes used training-history-only tertiles separately for every
  outer fold. Evaluation values never fitted regime cutoffs.
- Uncertainty used 1,000 outer-fold-stratified feature-session cluster bootstrap replicates, seed
  `20260827`, and 95% percentile intervals.
- F3's temporal coverage-concentration warning remains a data limitation.

## 4. Overall ranking result

| Model | Mean Spearman | Mean top-10% lift | Bootstrap 95% CI: Spearman | Bootstrap 95% CI: top-10% lift | Mean top-20% lift |
| --- | ---: | ---: | ---: | ---: | ---: |
| Persistence | 0.0608 | 1.1766 | 0.0412–0.0799 | 1.1220–1.2380 | 1.1057 |
| Ridge | **0.1940** | 1.3542 | **0.1725–0.2142** | 1.2838–1.4237 | **1.2913** |
| HGB | 0.1863 | **1.3611** | 0.1658–0.2047 | **1.2990–1.4251** | 1.2903 |

Ridge and HGB both materially outperform persistence as historical rankers. Their bootstrap
intervals overlap substantially, and their mean Spearman difference remains inside the frozen
`0.01` practical-tie margin. F6 therefore does not claim that one is statistically superior.

The top-decile interpretation is descriptive: rows ranked in the highest 10% had, on average,
approximately 35–36% larger realized stock-normalized volatility surprise than the full outer
fold. It is not a directional-return or profit statement.

## 5. Outer-period robustness

| Outer period | Ridge Spearman | Ridge top-10% lift | Ridge monotonic steps / 9 | HGB Spearman | HGB top-10% lift | HGB monotonic steps / 9 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2017–2018 | 0.1576 | 1.3257 | 8 | 0.1499 | 1.3374 | 8 |
| 2019–2020 | 0.2109 | 1.4403 | 8 | 0.1679 | 1.4051 | 7 |
| 2021–2022 | 0.1906 | 1.3981 | 9 | 0.1811 | 1.3930 | 7 |
| 2023 | 0.1091 | 1.1891 | 5 | 0.1349 | 1.2506 | 7 |
| 2024 | 0.2253 | 1.3537 | 8 | 0.2288 | 1.3668 | 6 |
| 2025 | 0.2727 | 1.4284 | 6 | 0.2801 | 1.5631 | 7 |
| 2026 partial | 0.1921 | 1.3440 | 7 | 0.1611 | 1.2114 | 6 |

Both candidates had positive Spearman and top-decile lift above one in every outer period. Decile
monotonicity was not perfect in most individual periods, especially Ridge in 2023. This variation
is retained rather than hidden. The 2017–2018 result must also be read with the F3 coverage warning.

## 6. Pooled outer-assigned deciles

The following pooled table preserves deciles assigned within each outer fold. Confidence intervals
come from feature-session cluster bootstrap. Pooled monotonicity was 9/9 adjacent non-decreasing
steps for both Ridge and HGB, although the per-period table above shows local deviations.

| Decile | Ridge realized mean (95% CI) | HGB realized mean (95% CI) |
| --- | ---: | ---: |
| D1 | 0.5413 (0.5101–0.5752) | 0.5541 (0.5214–0.5862) |
| D2 | 0.6605 (0.6295–0.6930) | 0.6871 (0.6533–0.7215) |
| D3 | 0.7289 (0.6931–0.7618) | 0.7452 (0.7128–0.7795) |
| D4 | 0.7346 (0.7004–0.7724) | 0.7513 (0.7172–0.7848) |
| D5 | 0.8294 (0.7866–0.8762) | 0.7927 (0.7577–0.8288) |
| D6 | 0.8391 (0.8025–0.8743) | 0.8544 (0.8125–0.8916) |
| D7 | 0.8798 (0.8393–0.9240) | 0.8662 (0.8294–0.9040) |
| D8 | 0.9610 (0.9153–1.0120) | 0.9325 (0.8833–0.9822) |
| D9 | 1.0334 (0.9851–1.0800) | 1.0200 (0.9774–1.0680) |
| D10 | 1.1395 (1.0810–1.2039) | 1.1442 (1.0869–1.2034) |

Persistence reached only 4/9 pooled non-decreasing steps (`D1=0.7920`, `D10=0.9828`), supporting
the incremental ranking value of the fitted candidates over the naive baseline.

## 7. Ticker robustness

- Ridge Spearman was positive for all ten tickers: range 0.1413 (`2317`) to 0.2173 (`2330`).
- HGB Spearman was positive for all ten tickers: range 0.1131 (`2412`) to 0.2197 (`0050`).
- Ridge top-decile lift exceeded one for all tickers: range 1.2430–1.4697.
- HGB top-decile lift exceeded one for all tickers: range 1.2399–1.4644.
- Persistence had negative Spearman for `0050` (-0.0145) and top-decile lift below one (0.9909).

These are subgroup diagnostics in a fixed ten-ticker universe. They are not evidence of broad
Taiwan-market generalization and were not used to alter either model.

## 8. Historical volatility-regime robustness

| Axis / regime | Ridge Spearman | Ridge top-10% lift | HGB Spearman | HGB top-10% lift |
| --- | ---: | ---: | ---: | ---: |
| Stock LOW | 0.1322 | 1.2559 | 0.1247 | 1.2515 |
| Stock MIDDLE | 0.1462 | 1.2947 | 0.1409 | 1.3008 |
| Stock HIGH | 0.2033 | 1.4858 | 0.1827 | 1.5080 |
| Market LOW | 0.1335 | 1.1765 | 0.1274 | 1.2226 |
| Market MIDDLE | 0.1305 | 1.2650 | 0.1203 | 1.2896 |
| Market HIGH | 0.2125 | 1.5262 | 0.1970 | 1.4954 |

Both candidates remained positive across all stock and market regimes, but ranking/lift was
stronger in historically high-volatility contexts. This is regime heterogeneity, not permission to
fit regime-specific models or thresholds.

## 9. Interpretation and limitations

Supported by F6:

- Ridge and HGB provide reproducible historical ranking information beyond naive persistence.
- Higher pooled predicted buckets correspond to higher realized relative volatility surprise.
- The signal remains positive across seven time periods, ten tickers and training-defined regimes.

Not supported by F6:

- exact future-surprise magnitude accuracy—the F5 average R² values remain near zero;
- prospective or independent external validity;
- price direction, profitable trading or causal interpretation;
- universal Taiwan-equity generalization beyond the ten-ticker/provider snapshot;
- perfect decile monotonicity in every period;
- a statistically decisive Ridge-versus-HGB winner.

## 10. Stop boundary

F6 is complete. `final_model_selected=false`, `model_artifact_persisted=false` and
`m7_rerun_performed=false` remain enforced. The next minimum executable unit, only after user
review/approval, is **F7 — Final Research Model Freeze**, which must apply the already-frozen model
selection rule without reopening F5/F6 tuning.
