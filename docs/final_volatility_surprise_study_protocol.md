# Final Study Protocol — Stock-Normalized Volatility Surprise Forecasting

Protocol version: `stock-normalized-volatility-surprise-final-v1`  
Milestone: `F1 — Final Research Protocol Freeze`  
Status: **FROZEN — Track A complete; F8/F10/F11A complete; F11B pending; optional F9 not run**
Canonical config SHA-256:
`4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66`

## 1. Final research identity

English title:

> Stock-Normalized Volatility Surprise Forecasting with Financial NLP Intelligence

Chinese title:

> 基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統

Product name: **Financial AI Assistant**.

Primary research question:

> Can leakage-safe price, volume, volatility and market-context features forecast next-session
> volatility surprise relative to each stock's own historical volatility context?

Secondary questions ask whether the nonlinear candidate improves over naive/Ridge baselines,
whether predictions rank ticker-sessions consistently, whether performance is robust by time,
ticker and regime, and—optionally—whether timestamp-safe NLP adds incremental value.

## 2. Research framing and historical integrity

This is a **retrospective, leakage-aware, hypothesis-informed final study**. The exploratory binary
`HIGH_RISK`/`NORMAL` study revealed threshold and regime sensitivity. Its M9 conditional analysis
showed that stock-relative volatility surprise was more stable than unconditional absolute-
volatility interpretation. That evidence motivated this continuous formulation.

The formulation is therefore not preregistered before all historical evidence. Previously
inspected 2025–2026 rows may participate as chronological historical outer folds, but no period is
renamed a pristine untouched final test, prospective validation or independent external
validation. Prospective external validity remains future work and is not required to complete the
portfolio.

M7–M11 reports, configs, artifacts and hashes remain immutable exploratory research history. F1
does not rerun, relabel or reinterpret the one M7 evaluation as new evidence.

## 3. Observed data coverage

Read-only inspection of the existing immutable market snapshot established:

- Market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`.
- Individual-stock rows: 40,691 across ten fixed tickers.
- TAIEX benchmark sessions: 4,080.
- Observed stock and benchmark range: 2010-01-04 through 2026-08-26.
- Existing pre-test feature snapshot: 28,690 rows, 2011-01-03 through 2024-12-30.
- Stock source: Yahoo research adapter; benchmark source: FinMind
  `TaiwanStockTotalReturnIndex/TAIEX` under the documented non-commercial research boundary.

F2 must rebuild one final-study dataset across all eligible history and report its actual row,
ticker/fold and exclusion counts. These counts are deliberately not invented in F1. Provider rows
and large snapshots remain ignored; public evidence is raw-free and hash-linked.

## 4. Frozen primary target

For ticker `i`, feature session `t` and the next observed exchange session `t+1`:

```text
r(i,s)       = ln(adjusted_close(i,s) / adjusted_close(i,s-1))
sigma20(i,t) = population_std(r(i,t-19), ..., r(i,t)); ddof = 0
y(i,t+1)     = abs(ln(adjusted_close(i,t+1) / adjusted_close(i,t))) / sigma20(i,t)
```

The primary target name is `next_session_stock_normalized_abs_log_return_v1`.

- `sigma20(i,t)` uses exactly 20 adjusted-close log-return transitions ending at `t` and is known
  post-close at `t`.
- `t+1` adjusted close enters only the target numerator. It may never enter predictors,
  preprocessing, imputation, feature selection or regime construction for row `t`.
- `t+1` is the next observed TAIEX exchange session, not the next calendar date and not a later
  substitute when the immediate required stock bar is absent.
- A row is excluded and counted if `sigma20(i,t) <= 1e-8`, or if numerator, denominator or target is
  non-finite. There is no clipping or silent epsilon replacement in the target.
- Values are quantized to `1e-12` for deterministic snapshots.
- Trainable models fit `log1p(y)` and return `max(0, expm1(prediction))` for original-scale
  evaluation. This deterministic transform has no globally fitted parameter.

This formula reuses the existing leakage-tested normalized continuous outcome, with the additional
explicit near-zero denominator gate frozen before F2. The target is nonnegative and continuous;
no 90th-percentile label or classifier threshold is required.

Secondary robustness outcomes are frozen as:

1. next-session absolute adjusted-close log return;
2. next-session high-low log range;
3. next-session Parkinson volatility proxy;
4. additive surprise: next absolute log return minus `sigma20(i,t)`.

They cannot replace the primary target after observing model results.

## 5. Dataset row and information contract

Final dataset version: `final-volatility-surprise-dataset-v1`.

Each row must contain ticker, feature session, exact target session, timezone-aware information
cutoff, fixed feature mapping, continuous target and source lineage. Identity is
`(ticker, feature_session)` and must be unique. Each row records market/config/snapshot hashes.

Random splitting, forward filling across a missing required market bar, global preprocessing and
provider-row redistribution are prohibited. The builder must report exclusions by reason and prove
that changing `t+1` changes the target but not the `t` feature hash.

## 6. Frozen market feature set

F1 reuses the compact 23-feature `risk-features-v1` foundation. F3 must audit each formula and
availability timestamp before reuse.

| Group | Frozen fields | Availability |
| --- | --- | --- |
| Price | log returns 1/5/10/20; overnight gap; MA deviation 5/20 | Post-close `t`; windows end at `t` |
| Volume | one-session log change; 20-session z-score; zero-volume flag | Post-close `t` |
| Volatility/range | log-return volatility 5/20; current high-low range; normalized ATR14; Parkinson mean5 | Post-close `t`; windows end at `t` |
| Technical | RSI14; normalized MACD12/26 and signal9 | Post-close `t` |
| Market context | TAIEX return 1/20; TAIEX volatility20; stock-minus-market return1; TAIEX drawdown20 | Same exchange session, post-close `t` |

There is no automated feature selection in v1. Complete, finite rows are required; missing features
cause an explicit abstention and count. Ridge scaling is fitted only inside the current inner/outer
training fold. HGB receives the same fixed features without scaling. NLP is not a core feature.

## 7. Outer rolling-origin evaluation

All folds are retrospective historical out-of-sample periods. Training targets must finish before
evaluation starts; boundary rows with an overlapping target are purged.

| Outer fold | Training history | Evaluation period | F1 sample count |
| --- | --- | --- | --- |
| `outer_2017_2018` | 2011-01-01–2016-12-31 | 2017-01-01–2018-12-31 | Determined in F2 |
| `outer_2019_2020` | 2011-01-01–2018-12-31 | 2019-01-01–2020-12-31 | Determined in F2 |
| `outer_2021_2022` | 2011-01-01–2020-12-31 | 2021-01-01–2022-12-31 | Determined in F2 |
| `outer_2023` | 2011-01-01–2022-12-31 | 2023-01-01–2023-12-31 | Determined in F2 |
| `outer_2024` | 2011-01-01–2023-12-31 | 2024-01-01–2024-12-31 | Determined in F2 |
| `outer_2025` | 2011-01-01–2024-12-31 | 2025-01-01–2025-12-31 | Determined in F2 |
| `outer_2026_partial` | 2011-01-01–2025-12-31 | 2026-01-01–2026-08-26 | Determined in F2 |

The 2025 and 2026 folds were previously inspected in binary exploratory work. Their inclusion is
efficient retrospective reuse, not a renewed sealed test.

## 8. Inner temporal validation

Hyperparameters are selected separately inside each outer training history. The inner procedure
uses the latest three complete calendar years, one year per validation block, with expanding
training from 2011. No outer evaluation row or target may enter this process.

| Outer fold | Inner validation years |
| --- | --- |
| `outer_2017_2018` | 2014, 2015, 2016 |
| `outer_2019_2020` | 2016, 2017, 2018 |
| `outer_2021_2022` | 2018, 2019, 2020 |
| `outer_2023` | 2020, 2021, 2022 |
| `outer_2024` | 2021, 2022, 2023 |
| `outer_2025` | 2022, 2023, 2024 |
| `outer_2026_partial` | 2023, 2024, 2025 |

Within a candidate model, select hyperparameters by highest mean inner Spearman, then lower mean
inner MAE, higher worst-inner Spearman, lower complexity and deterministic lexical parameter
order. The selected setting is refit on the full outer training history and evaluated once on that
outer block.

## 9. Frozen model set

### Model 0 — normalized-move persistence

```text
prediction = abs(return_log_1) / max(volatility_log_return_20, 1e-8)
```

This uses only post-close `t` features and has no fitted parameter.

### Model 1 — Ridge Regression

Scikit-learn Ridge on the fixed feature set, fold-local `StandardScaler`, and alpha grid
`[0.1, 1, 10, 100]`.

### Model 2 — HistGradientBoostingRegressor

The main nonlinear candidate uses fixed grids for learning rate `[0.03, 0.05]`, 200 iterations,
leaf nodes `[15, 31]`, minimum leaf samples `[20, 50]`, L2 `[0, 1]`, disabled early stopping and
seed `20260827`.

XGBoost is excluded from F1 because the dependency is absent and its incremental value is not yet
justified. LSTM, Transformer and other neural price models are prohibited in v1.

## 10. Model selection and evaluation

Every model produces predictions for every eligible outer block. The final research model is
selected by highest mean outer-fold Spearman. A difference of at most `0.01` is a practical tie;
within a tie prefer lower mean outer MAE, higher worst-fold Spearman and lower implementation
complexity. One lucky year cannot decide the winner.

Required original-scale regression metrics:

- MAE;
- RMSE;
- R².

Required ranking metrics:

- Spearman rank correlation / rank IC;
- top-decile lift ratio;
- top-quintile lift ratio;
- realized target summaries by predicted-score decile.

For fraction `q` in an outer fold:

```text
lift(q) = mean(realized primary target among highest predicted q fraction)
          / mean(realized primary target among all eligible rows in that outer fold)
```

The primary target is nonnegative. If the fold-wide realized mean is zero or undefined, ratio lift
is reported as undefined rather than replaced. Top counts use the highest `ceil(q*n)` predictions.
Ties are resolved deterministically by predicted score descending, feature session ascending and
ticker ascending.

Each outer fold is split into ten equal-frequency predicted-score buckets. For every bucket report
sample count, mean prediction, mean/median realized target and dispersion/uncertainty. Perfect
monotonicity is not required; violations remain visible.

## 11. Robustness and uncertainty

Report MAE, RMSE, Spearman and top-decile lift by outer fold, ticker, historical stock-volatility
regime, defensible TAIEX regime and predicted decile. Regime cutoffs must be fitted only from the
corresponding historical training period. Subgroups are diagnostics and cannot trigger another
tuning round.

Where sample size permits, use 1,000 feature-session cluster bootstrap replicates with seed
`20260827` and 95% percentile intervals. Small or single-class-like degenerate groups are marked
insufficient rather than hidden.

## 12. Product score and communication bands

The model outputs a continuous predicted volatility-surprise score. After F7 model selection, the
historical reference distribution is the selected model's pooled outer-fold OOF predictions.
Frozen percentiles define presentation bands:

- below 50th percentile: LOW;
- 50th to below 80th: MODERATE;
- 80th to below 95th: HIGH;
- 95th and above: VERY HIGH.

These are communication/ranking bands, not classifier labels. Inference must return ticker,
as-of/cutoff, predicted score, historical percentile, band, model version and feature-pipeline
version. The UI states that this is relative volatility-surprise risk, not price direction,
investment advice or guaranteed volatility.

## 13. Financial NLP Intelligence boundary

Track B remains required as a product intelligence layer, not as a prerequisite for Track A
accuracy. Preserve pinned English FinBERT, Chinese diagnostic failures, FSC 6,021-record filtered
corpus, BERT/MacBERT feasibility evidence, frozen representation candidate, TWSE announcement
processing, weak supervision, source governance and Eland HOLD/exclusion.

An optional market-only versus market+NLP ablation may run only when timestamp-safe features already
exist. It uses the same outer folds and model budget. Null/negative results are acceptable, and
unsupported Chinese sentiment must abstain rather than fabricate polarity probabilities.

## 14. Automated safety requirements

F2–F6 must test:

1. no random split;
2. unique ticker/feature-session identity;
3. exact next observed exchange target session;
4. timezone-aware information cutoff on `t`;
5. `t+1` mutation changes target, never `t` features;
6. rolling features and denominator end at `t`;
7. target/future fields cannot enter predictors;
8. training target finishes before inner/outer validation;
9. preprocessing fits only current training rows;
10. inner selection cannot access outer validation;
11. dataset/config/model/OOF hashes reproduce deterministically where feasible;
12. previously inspected periods are never described as a new sealed test.

## 15. F1 stop boundary

F1 creates only plans, schemas and safety tests. It authorizes no dataset rebuild, model fitting,
outer evaluation, final result, API integration, deployment, GAS change, commit or push. The next
minimum executable unit after review is **F2 — Historical Dataset Rebuild**.

## 16. F2 implementation record

After separate user approval, F2 rebuilt the immutable historical dataset without changing this
F1 protocol. It produced 32,357 eligible rows from 38,290 candidates for feature dates
2011-01-03–2026-08-25. The dataset SHA-256 is
`2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.

The rebuild fitted no preprocessing/model and created no binary label. It documented 5,933 strict
session-availability exclusions, including systematic provider/benchmark gaps, rather than
imputing or substituting later bars. See `research/evaluation/f2_historical_dataset_result.md`.
At the F2 stop boundary, F3 had not started.

## 17. F3 implementation record

After separate approval, F3 independently reproduced all 32,357 targets from immutable market
bars, verified exact next-session alignment, the complete 23-feature availability contract and all
dataset/feature/row hashes. It fitted no preprocessing or model.

The predeclared coverage-bias audit found no abnormal ticker or known-volatility-regime
concentration. It did find abnormal exclusion concentration in calendar years 2012, 2013, 2016,
2017 and 2019, plus `outer_2017_2018`; 7.10% of evaluation candidates also lacked enough bars for a
regime assignment. The coverage warning therefore cannot be fully downgraded. Its frozen
classification is `DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION`, documented in
`research/evaluation/f3_target_feature_coverage_audit_result.md`. At the F3 stop boundary, F4 had
not started.

## 18. F4 implementation record

After separate approval, F4 implemented the three frozen candidate families: parameter-free
normalized persistence, four Ridge alphas with training-only StandardScaler, and sixteen HGB
parameter combinations with internal early stopping disabled. Trainable candidates fit `log1p(y)`
and invert to the nonnegative original scale.

Every fit requires an explicit temporal context and rejects target overlap, non-training rows,
duplicate identities, non-finite data and parameters outside the F1 grid. Synthetic repeated fits
produced identical manifests and predictions. F4 ran no historical outer evaluation, selected no
hyperparameters/winner and persisted no final model. See
`research/evaluation/f4_regression_candidates_result.md`. At the F4 stop boundary, F5 had not
started.

## 19. F5 implementation record

After separate approval, F5 ran the seven frozen outer periods. Every candidate setting was scored
only on the three inner temporal validations contained in the corresponding outer training
history; the selected setting was refitted on full outer training and evaluated once on the later
outer block. Fold-local preprocessing and temporal-boundary guards remained active.

The run produced 20,637 unique historical OOS rows and 61,911 immutable OOF prediction rows across
persistence, Ridge and HGB. Canonical OOF SHA-256 is
`b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7`. Mean outer Spearman was
0.0608, 0.1940 and 0.1863 respectively. Ridge and HGB are within the frozen `0.01` practical-tie
margin, while their mean R-squared values remain near zero/slightly negative. F5 therefore records
a modest ranking signal and selects no final model. F6 must analyze the immutable OOF predictions
without retuning; F7 remains responsible for final selection. See
`research/evaluation/f5_nested_temporal_evaluation_result.md`.

## 20. F6 implementation record

After separate approval, F6 joined every immutable F5 OOF prediction back to its exact F2 source
row, fitted stock/market regime tertiles only on the relevant outer training history, assigned
deciles within model/outer fold and ran 1,000 outer-fold-stratified feature-session cluster
bootstrap replicates.

Ridge/HGB mean Spearman was 0.1940/0.1863 and mean top-decile lift was 1.3542/1.3611. Both had
positive ranking and lift above one across every outer period, ticker and historical regime. Their
pooled outer-assigned realized-target deciles were 9/9 non-decreasing, while individual periods
showed 5–9 steps; model bootstrap intervals overlapped. F6 therefore preserves the practical tie,
performs no retuning and selects no final model. Canonical analysis SHA-256 is
`8fd2fdc84f65fb47b6bc87df4b662c4bbd5a9ec8c82d41de4cdd3825b6364e70`. See
`research/evaluation/f6_ranking_robustness_result.md`.

## 21. F7 implementation record

After separate approval, F7 applied the frozen practical-tie sequence to immutable F6 evidence.
Ridge and HGB were within `0.01` mean outer Spearman; Ridge was selected by the first applicable
tie-break, lower mean outer MAE. No individual fold, ticker or regime drove selection.

The same temporal rule over 2023–2025 selected Ridge alpha 100. The final research model fitted all
32,357 eligible F2 rows through feature date 2026-08-25/target session 2026-08-26. It was serialized
as safe JSON—not pickle—with exact scaler/coefficient lineage, a 20,637-row Ridge historical OOF
reference, empirical percentile and frozen 50/80/95 communication bands. Artifact SHA-256 is
`279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de`.

Artifact inference reproduced fitted Ridge predictions within `5.01e-13`. The model is frozen but
not deployed and does not claim prospective accuracy. See
`research/evaluation/f7_final_research_model_result.md`.

## 22. F8 implementation record

After separate approval, F8 froze a unified Financial NLP Intelligence output contract. English
polarity accepts only the pinned ProsusAI/finbert revision; without optional runtime inference it
returns `ELIGIBLE_NOT_SCORED`. Chinese/Taiwan polarity always returns explicit abstention and null
probabilities. Official TWSE metadata and deterministic event/impact proxies remain separate and
are never labeled sentiment ground truth.

The audit verified seven pre-existing evidence-file hashes and three controlled routing cases. It
ran no model download/inference/training, external API, LLM, manual annotation/review or deployment,
and persisted no source rows. Config SHA-256 is
`de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4`; aggregate analysis
SHA-256 is `8994a66e2fef70da2ad16d54cb3698ac8e2f14badad4e9237a03e2669b97ab42`. F9 remains
optional/non-blocking; F10 may follow directly after review.

## 23. F10 implementation record

After separate approval, F10 skipped the non-blocking F9 and integrated F7/F8 into two versioned
FastAPI research endpoints. Prediction requires the exact 23 finite F7 features plus a timezone-
aware cutoff and verifies the safe JSON artifact SHA before returning score, OOF percentile, band
and lineage. Intelligence reads stored database rows only; it performs no request-time provider,
FinBERT or LLM call and preserves Chinese polarity abstention.

The controlled audit registered both required routes and validated one synthetic contract input
without treating it as performance evidence or persisting its features/prediction. F10 config
SHA-256 is `b4367815b484352375b6693d91b44298b8e4dc3b84bf0a3c69f956f97175a4f2`; analysis
SHA-256 is `dc26d6f13e07c27e8ec32b6da8d06ac6fb1fed9b5fff32040a9d69221394b5fb`.
No external API, training, GAS change, M7 rerun or deployment occurred.

## 24. F11A implementation record

After separate approval, F11A created a Streamlit dashboard with a deterministic controlled-offline
mode and an optional loopback-only F10 API mode. The fixed fixture uses the exact 23-feature contract
and an F7 artifact prediction over synthetic values; it is explicitly not a real ticker observation
or evaluation result. Chinese sentiment abstains, English remains eligible-not-scored and event
proxies remain non-ground-truth metadata.

Config SHA-256 is `0f70c88b6ea3b6e21177ae2fce6a4bef17d1b02a89a0dd7d491d425663ebc267`;
fixture SHA-256 is `c55f546ebe9ee94f616d518c205c18acb6b35683436dce1a312e7849c2935c06`.
F11A made no external request in offline mode, modified no GAS, and performed no deployment. R0
later classified LINE/GAS work as separate pending F11B; this does not alter the F11A evidence.
