# Financial AI Assistant — Authoritative Handoff

Last revised: 2026-08-29

ACTIVE PHASE: **R1A Public Web Demo Release — READY FOR MANUAL DEPLOY / REDEPLOY REQUIRED**

NEXT EXECUTABLE UNIT: **R1B — only after user-controlled R1A commit/push and deployment review**

TRACK A: **COMPLETE / FROZEN — Ridge Regression, alpha 100**

TRACK B: **COMPLETE THROUGH B5 — optional B6/F9 not run and not required**

TRACK C: **F10/F11A/F11B-D0/1A/1B/2A/F12 complete / R1A ready / F11B-2 blocked**

AP11: **optional enhancement; not a prerequisite**

eLAND: **permanent historical exclusion; no active use, API call or re-audit**

GAS: **future modification authorized only through the verified immutable backup, migration-copy
and rollback rules; live behavior was not changed in R0**

Current source decision: **TWMD ACCEPT_SECONDARY — B2.1 contract/provider ready; B2 v1 unchanged,
no TWMD dataset rows were used by completed B3**

B3 representation decision: **FSC-adapted BERT-base-Chinese promoted for representation only;
Chinese sentiment remains ABSTAIN**

B3.1 label-source decision: **CFSC-ABSA HOLD; multilingual Chinese financial sentiment HOLD;
StockSentCN HOLD; gate answer NO; no B3.2**

B4 market-reaction decision: **corrected 2021–2025 TWMD backfill; 7,582 events / 3,433 aggregated
ticker-reaction windows / 9 tickers; MARKET_REACTION_MODEL = AUTOMATED_SIGNAL_ONLY**

## CURRENT REPOSITORY SNAPSHOT

- Local `main` and `origin/main` both point to `cb413a8` (`F11B-2`) at F12 finalization time.
- Current uncommitted changes preserve F11B-2A/F12 and add the R1A zero-secret, fixture-only
  Streamlit public release entrypoint, documentation and safety tests. No commit or push was made.
- Existing M-series and F1–F8/F10/F11A evidence remains preserved. F9/B6 is optional/not run.
- The canonical roadmap is `docs/r0_project_rebaseline_protocol.md`; older milestone stop text is
  historical evidence and does not override it.
- Local secret file `.env` is Git-ignored and untracked. Never display or commit its values.
- The supplied private GAS originals remain unchanged at the user-provided Desktop paths. Verified
  private copies now exist under ignored `.tools/private/gas-migration/r0-20260829/`; see
  `docs/gas_migration_safety_freeze.md`.

## ACTIVE PROJECT DIRECTION

Final English title:

> Stock-Normalized Volatility Surprise Forecasting with Financial NLP Intelligence

Final Chinese title:

> 基於機器學習之股票相對波動異常程度預測與金融 NLP 情報系統

Product name remains **Financial AI Assistant**.

Primary research question:

> Can leakage-safe price, volume, volatility and market-context features forecast next-session
> volatility surprise relative to each stock's own historical volatility context?

Track A predicts a continuous next-session stock-normalized volatility-surprise score and is now
complete/frozen. Track B is the active Taiwan Financial Sentiment / Impact Modeling and Financial
NLP Intelligence program. Track C is the Python/FastAPI product with F11A and F11B-D0/1A/1B
complete. F11B-1B is deterministic, authenticated, read-only and not deployed. F11B-2A confirms
official 10/10 current coverage but only 5/23 exact features; F11B-2 remains gated.

## SINGLE AUTHORITATIVE EXECUTION SEQUENCE

```text
R0 Project Rebaseline & GAS Safety Freeze
  → B1 Source Candidate Audit
  → B2 Taiwan Financial Text Dataset
  → B3 Domain Adaptation & Candidate Signals
  → B3.1 Chinese Sentiment Label Source Audit
  → B4 Validation / Abstention Decision
  → B5 NLP Intelligence Integration
  → F11B-D0 LINE UX + Multi-user + GAS/FastAPI Design Freeze
  → F11B-0 GAS Immutable Backup & Migration Copy (safety prerequisite already complete)
  → F11B-1A Controlled LINE Routing in Migration Copy
  → F11B-1B Controlled Read-only Demo
  → F11B-2 Current-Market Feature / Risk Integration (only if separately validated)
  → B6 / F9 Optional NLP Incremental-Value Study
  → F12 Portfolio Finalization
  → R1A Public Web Demo Release
  → R1B LINE Controlled Demo Release (only after R1A success or ready/manual release)
```

R0 created the F11B-0 private safety copies early without altering the sequence. B1, B2, B2.1, B3,
B3.1, B4, B5 and F11B-D0/1A/1B/2A/F12 are complete. R1A is ready for manual deploy. Do not begin
F11B-2 unless all applicable gates pass under a separately approved milestone. Definitions of Done are frozen in
`docs/r0_project_rebaseline_protocol.md`.

F11B-1B is complete and not deployed. F11B-2A found official TWSE current OHLCV for all ten frozen
tickers and exact TAIEX total-return parity, but historical Yahoo `adjclose` cannot be reproduced
from the audited official corporate-action lineage. Only 5/23 features pass; the updated gate is
6/9 and `NOT_READY_FOR_F11B_2`. F12 is not blocked by this result.

## WHY THE FORMULATION CHANGED

The binary `HIGH_RISK`/`NORMAL` study is not deleted and is not described as a failure. It is now
**Exploratory Binary-Risk Research / Problem-Formulation Evidence**.

The exploratory work showed substantial threshold-dependent precision/recall trade-offs and
regime-dependent operating behavior. M11 reduced cross-regime recall/specificity dispersion with
LOW 0.12／MIDDLE 0.10／HIGH 0.08, but overall MCC fell. M9 also showed that aggregate raw absolute-
volatility comparisons reversed after stock-volatility conditioning, while normalized and additive
surprise outcomes were much more consistent.

Authoritative wording:

> The exploratory binary-risk formulation revealed substantial threshold and regime sensitivity.
> Conditional analysis showed that the more stable signal was stock-relative volatility surprise
> rather than unconditional absolute volatility. The final study therefore reformulates the task
> as continuous stock-normalized volatility-surprise forecasting.

## RESEARCH INTEGRITY BOUNDARY

The final study is:

`RETROSPECTIVE_LEAKAGE_AWARE_HYPOTHESIS_INFORMED_FINAL_STUDY`

The historical data has already informed research decisions. Therefore no historical period may
be presented as a new pristine untouched test, prospective validation, independent external
validation or preregistered confirmation.

Previously inspected 2025–2026 rows may be included as historical outer rolling-origin periods,
but must be called retrospective historical OOS evidence. The project no longer waits for a new
126-session/six-month holdout. Naturally future data remains useful **Future External Validation**,
not a completion requirement.

Never rerun M7. Evaluation sequence remains exactly one.

## FROZEN PRIMARY TARGET

Version: `next_session_stock_normalized_abs_log_return_v1`.

```text
r(i,s)       = ln(adjusted_close(i,s) / adjusted_close(i,s-1))
sigma20(i,t) = population_std(last 20 adjusted-close log returns ending at t); ddof=0
y(i,t+1)     = abs(ln(adjusted_close(i,t+1) / adjusted_close(i,t))) / sigma20(i,t)
```

- `sigma20` is available post-close at `t`.
- `t+1` is the exact next observed TAIEX exchange session.
- `t+1` adjusted close is target-only.
- Exclude/report rows when `sigma20 <= 1e-8` or any component is non-finite.
- Do not clip the target or silently replace the denominator.
- Quantize to `1e-12`.
- Trainable models fit `log1p(y)` and evaluate `max(0, expm1(prediction))` on the original scale.

This reuses the existing leakage-tested normalized continuous outcome and adds a frozen near-zero
gate. Secondary outcomes are raw absolute log return, high-low log range, Parkinson proxy and
additive absolute-return surprise versus `sigma20`.

## VERIFIED HISTORICAL COVERAGE

Read-only local inspection found:

- market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`;
- 40,691 stock rows across ten tickers;
- 4,080 TAIEX benchmark sessions;
- observed market coverage 2010-01-04–2026-08-26;
- existing pre-2025 feature dataset 28,690 rows, 2011-01-03–2024-12-30;
- stock provider Yahoo research adapter and FinMind TAIEX total-return benchmark.

F2 produced 32,357 eligible rows from 38,290 candidates and excluded 5,933 rows under the frozen
strict-session contract. Feature coverage is 2011-01-03–2026-08-25 and the immutable dataset
SHA-256 is `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.
No preprocessing/model/binary label was created. See
`research/evaluation/f2_historical_dataset_result.md`.

## FROZEN TEMPORAL DESIGN

Outer rolling-origin periods:

| Fold | Train | Historical outer evaluation |
| --- | --- | --- |
| `outer_2017_2018` | 2011–2016 | 2017–2018 |
| `outer_2019_2020` | 2011–2018 | 2019–2020 |
| `outer_2021_2022` | 2011–2020 | 2021–2022 |
| `outer_2023` | 2011–2022 | 2023 |
| `outer_2024` | 2011–2023 | 2024 |
| `outer_2025` | 2011–2024 | 2025 |
| `outer_2026_partial` | 2011–2025 | 2026-01-01–2026-08-26 |

Each outer fold selects hyperparameters only inside its training history using the latest three
complete one-year inner validations:

- 2014/2015/2016;
- 2016/2017/2018;
- 2018/2019/2020;
- 2020/2021/2022;
- 2021/2022/2023;
- 2022/2023/2024;
- 2023/2024/2025.

Inner primary selection metric is mean Spearman, then mean MAE, worst-inner Spearman, lower
complexity and deterministic parameter order. Outer validation never fits imputation, scaling,
features, transforms or hyperparameters. Boundary targets overlapping evaluation are purged.

## FROZEN MODEL AND METRIC SET

Models:

1. normalized-move persistence baseline;
2. Ridge Regression with fold-local StandardScaler and alpha `[0.1,1,10,100]`;
3. HistGradientBoostingRegressor with the small grid frozen in
   `research/configs/final_volatility_surprise_study.v1.json`.

XGBoost is excluded from F1 because the dependency and incremental value are not justified. Neural
price models are not allowed.

Required metrics:

- MAE, RMSE, R²;
- Spearman/rank IC;
- top-decile and top-quintile lift ratios;
- realized target by predicted-score decile;
- outer-fold/ticker/stock-regime/market-regime robustness;
- feature-session cluster bootstrap uncertainty where practical.

Select the final model by mean outer Spearman. Differences `<=0.01` are practical ties; then prefer
lower mean MAE, higher worst-fold Spearman and lower complexity. One lucky period cannot select a
winner.

## PRODUCT OUTPUT BOUNDARY

The final inference contract will return ticker, as-of/cutoff, predicted surprise score, historical
percentile, communication band, model version and feature-pipeline version.

LOW/MODERATE/HIGH/VERY HIGH are presentation bands from selected-model historical OOF prediction
percentiles 50/80/95. They are not classifier labels. Product copy must state:

> This is a relative volatility-surprise risk score, not a prediction of price direction.

Also state research-only, not investment advice and no guaranteed future volatility.

## EXPLORATORY / FROZEN BINARY RESEARCH

Preserve every historical report, config, model artifact and hash:

- M6 candidate manifest:
  `951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`.
- M7 sealed evaluation:
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`.
- M8 robustness analysis:
  `c7e82d99f6e0ea922d93eaba1069b28d5cdad84c1f0a6d01fb4b3cc6cc20d56b`.
- M9 conditional analysis:
  `5135925bf36fc5698d07fe31a19524f0a50944fcd9cd56132341cabe91f13da2`.
- M10 operating-point analysis:
  `21b77b55dac40c9c8922f7306a21d474b14fd04a41a584723c4c74098a01f83c`.
- M11 regime-threshold analysis:
  `76b5e0335fab9699955b1e9983b5105f735d34d46390184ca25dffad88cf3b88`.

Historical facts remain:

- M7: 3,647 rows, recall 0.508, precision 0.180, MCC 0.155, PR-AUC 0.189, Brier 0.0926;
- M8: material ticker/time/regime heterogeneity;
- M9: raw aggregate/within-regime reversal and stable normalized/additive surprise;
- M10: development thresholds 0.09/0.11/0.13 with substantial trade-offs;
- M11: 73/125,000 eligible triplets, selected 0.12/0.10/0.08, lower dispersion but lower MCC.

These are not the final production model. Do not delete, rerun, retrospectively rewrite or use
them to claim a pristine final test.

## TRACK B — PRESERVE ALL NLP EVIDENCE

Preserve:

- `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43` and English polarity outputs;
- historical 12-item English sanity evidence only;
- Chinese diagnostic macro-F1 0.320/0.357/0.442/0.592/0.640; no candidate passed the gate;
- zero-manual-label/abstention protocol;
- filtered 6,021-record FSC family-isolated corpus;
- BERT-base-Chinese/MacBERT feasibility and 200-step pilot;
- frozen BERT-base-Chinese representation candidate, not sentiment truth;
- TWSE announcement processing, market reaction and weak-supervision infrastructure;
- TWSE/FinMind/TEJ source and licensing audits;
- Eland permanent `HOLD / excluded from active modeling` record.

Chinese sentiment currently **must abstain**. Never fabricate Positive/Neutral/Negative
probabilities. Track B now follows exactly:

1. **B1 Source Candidate Audit** — complete; source decisions and whitelist frozen;
2. **B2 Taiwan Financial Text Dataset** — complete; normalized snapshot/update contract frozen;
3. **B3 Domain Adaptation & Candidate Signals** — complete; one frozen domain encoder and distinct
   signal candidates;
4. **B3.1 Chinese Sentiment Label Source Audit** — complete; three candidates HOLD, gate answer NO;
5. **B4 Market Impact / Reaction Validation** — complete; corrected five-year backfill passed the
   data gate; metadata magnitude signal is `AUTOMATED_SIGNAL_ONLY`, while BERT text incremental
   value is unsupported;
6. **B5 NLP Intelligence Integration** — complete; F8/F10 reused with a backward-safe Track B
   extension and explicit capability separation;
7. **B6/F9 optional incremental-value study** — same frozen Track A discipline, non-blocking.

B4 did not reinterpret returns as linguistic sentiment. Its primary target was frozen as
next-eligible-session signed abnormal return relative to TAIEX, with absolute abnormal return as a
secondary magnitude outcome. A corrected 2021–2025 private backfill passed the data gate and ran
three rolling-origin folds. The project retains the zero-manual-label, zero-manual-review and
no-human-adjudication requirements.

AP11 is an optional future source enhancement, not required before Chinese NLP, F11B or F12. eLAND
is prohibited permanently from datasets, models, APIs, audits, weak supervision, features,
training and candidate comparisons; retain only its historical rejection record.

### B1 source decision at this handoff

Authoritative report: `research/evaluation/b1_source_candidate_audit.md`. Machine-readable
authority: `research/configs/b1_source_candidate_manifest.v1.json`.

- **ACCEPT_PRIMARY:** FSC filtered 6,021-record domain corpus; TWSE daily official material
  information OpenAPI.
- **ACCEPT_SECONDARY:** TPEx daily official material information OpenAPI; GDELT GKG/GAL metadata.
- **CONDITIONAL:** FinMind `TaiwanStockNews` for deduplicated later-period title/link discovery only.
- **OPTIONAL_FUTURE:** TEJ/AP11 (`OPTIONAL_HIGH_QUALITY_OFFICIAL_SOURCE`); TWSE Data E-Shop MOPS
  distribution.
- **HOLD (historical frozen B1 manifest):** interactive historical MOPS automation, TWMD,
  `tw-finance-159M`, derived `tw-fsc`,
  Cnyes/Anue, Yahoo Taiwan Finance, WantGoo, and eLAND as a permanent exclusion record.
- **REJECT:** none; eLAND's historically mandated label remains HOLD/excluded rather than being
  reclassified.

Frozen preferred B2 stack: FSC domain text + TWSE/TPEx official announcements + bounded GDELT
media metadata. Fallback: FSC + TWSE/TPEx only. Official announcements and media news remain
different source types; GDELT Tone is `MEDIA_TONE_PROXY`, never validated sentiment. Publisher
article bodies are not approved for fetching, caching, training or redistribution.

Post-B2 re-audit superseding operational status: **TWMD `ACCEPT_SECONDARY`** for major-event
taxonomy/title metadata and current issuer mapping only. The historical B1 manifest and B2 v1
whitelist stay immutable. Company news, the unavailable legacy material-information path and the
private-beta MOPS endpoint remain HOLD. See
`research/evaluation/twmd_pro_reaudit_result.md` and
`research/configs/twmd_pro_source_decision.v1.json`.

### B2.1 TWMD amendment

- Contract: `docs/b2_1_twmd_secondary_source_contract.md` and
  `research/configs/b2_1_twmd_secondary_source.v1.json`.
- Result: `research/evaluation/b2_1_twmd_secondary_source_result.md`.
- Provider/schema: `pipelines/news/twmd_major_events.py`.
- Runtime query is frozen to `ticker/date_from/date_to/limit`; every response must echo those
  values, and ticker/window/schema mismatches fail closed.
- Maximum request is one ticker, 31 days, 100 rows and 1 MB. Reaching the limit is rejected as
  possible truncation.
- Timestamps are Asia/Taipei under an explicit source-contract assumption because the API omits
  an offset.
- Rights tier is `LICENSED_EVENT_METADATA_PRIVATE`; no full text, sentiment truth or human-label
  claim is allowed.
- No TWMD dataset was ingested. Completed B3 used B2 v1 and zero TWMD rows.

### B3 domain adaptation and candidate signals

- Protocol/B4 candidate manifest:
  `research/configs/b3_domain_and_candidate_signals.v1.json`.
- Protocol document: `docs/b3_domain_and_candidate_signals_protocol.md`.
- Result: `research/evaluation/b3_domain_and_candidate_signals_result.md`.
- B3 integrity audit reused the completed 200-step FSC MLM pilot; it did not retrain or read the
  sealed FSC test file.
- BERT-base-Chinese revision `8f23c25b...` is the single promoted representation candidate;
  adapted weight SHA-256 is
  `eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`.
- No independent permissible sentiment-label source exists; no sentiment classifier, pseudo-label
  set, manual label/review or circular validation was created.
- Chinese sentiment remains `ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.
- Candidate categories remain separate: domain encoder, embedding, linguistic sentiment, event
  class, impact signal, market reaction and media tone.
- TWMD supplied contract/schema context only and zero rows. `event_class` is not sentiment.
- One bounded GDELT official RSS recovery kept TLS enabled and saved no raw payload; XML parsing
  failed, so implementation is temporarily unavailable/conditional and non-blocking.

### B3.1 Chinese sentiment label-source audit

- Authoritative report:
  `research/evaluation/b3_1_chinese_sentiment_label_source_audit.md`.
- Machine-readable decision:
  `research/configs/b3_1_chinese_sentiment_label_sources.v1.json`.
- CFSC-ABSA is `HOLD`: aspect-level task, annotation provenance and exact news sources are not
  documented, no license exists, and sentence-family split isolation is unverified.
- `Kenpache/multilingual-financial-sentiment` Chinese subset is `HOLD`: its single unsplit file has
  no annotation method; Apache-2.0 metadata conflicts with academic/noncommercial-only card text
  and retained publisher copyright.
- StockSentCN is `HOLD`: the base is primarily emoji distant supervision, 9.05M rows are model
  pseudo-labels, the 900 expert rows are not released/separable, the repository has no full dataset
  or license, and its task is investor mood/direction rather than news linguistic sentiment.
- Clean training source: no. Independent evaluation source: no. Exact gate answer: `NO`.
- B3.2 was not created. No sentiment model training, manual labels, eLAND use, GAS change or Track A
  change occurred.

### B4 market impact / reaction validation

- Frozen protocol: `docs/b4_market_reaction_validation_protocol.md` and
  `research/configs/b4_market_reaction_validation.v1.json`.
- Authoritative result: `research/evaluation/b4_market_reaction_validation_result.md`.
- Correction: the initial four rows came from two intentional `limit=2` entitlement/schema probes
  and were not a historical dataset. The first insufficiency conclusion was superseded before B4
  finalization.
- Private 2021–2025 monthly backfill over the frozen ten-ticker universe produced 7,582 events;
  deterministic family/window aggregation left 3,433 windows across nine represented tickers.
- FSC supplied 6,021 domain-adaptation documents but no ticker/timestamp-ready event rows; the old
  M8 TWSE evidence is target-only and concentrated in two days; TPEx and GDELT had zero admitted
  historical rows.
- Publication-time rules use Asia/Taipei and observed exchange sessions: before open maps prior
  close to same close; intraday abstains with daily prices; after close maps same close to next
  close; weekends/holidays map prior close to next exchange close; unknown timezone abstains.
- Primary target is stock simple return minus TAIEX total-return-index return; secondary target is
  its absolute value. This is subsequent market reaction, not sentiment or causal impact.
- Three rolling folds train on earlier years and evaluate 2023 (730), 2024 (713) and 2025 (688),
  using Ridge alpha 100 with fold-local scaling/category encoding.
- Signed OOF Spearman: market 0.0349, metadata 0.0784, BERT text+metadata 0.0408. Text-minus-metadata
  was negative in every fold and mean increment was -0.0394.
- Absolute-reaction metadata model achieved OOF Spearman 0.2504 and top-decile lift 1.623, with
  positive fold Spearman 0.1434/0.1960/0.3418. This is modest automated evidence, not validation.
- Exact maturity is `AUTOMATED_SIGNAL_ONLY`; Chinese linguistic sentiment independently remains
  `ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.
- Private TWMD manifest SHA-256 is
  `aa78324c80d12872c8a4023e26184673cdff90552fb8b41bb5b2a635e1f7149d`.
- At the B4 stop boundary, B5 had not started; Track A, GAS, LINE, FastAPI, Streamlit and deployment
  were unchanged.

### B5 NLP Intelligence Integration

- Protocol/config: `docs/b5_nlp_intelligence_integration_protocol.md` and
  `research/configs/b5_nlp_intelligence_integration.v1.json`.
- Result: `research/evaluation/b5_nlp_intelligence_integration_result.md`.
- Existing F8 assembler and F10 database-only endpoint were extended, not duplicated. Each item has
  an optional `track_b_intelligence` object, preserving response-v1 compatibility.
- Chinese polarity/probabilities and market direction are always null with explicit abstention.
- Stored B4 magnitude scores use frozen 50/80/95 percentile band thresholds; missing or cutoff-
  unsafe stored signals abstain. Maturity remains `AUTOMATED_SIGNAL_ONLY`.
- TWMD event class is separate inferred taxonomy; GDELT media tone is null/conditional proxy;
  FSC-adapted BERT is representation-only and is not used to claim prediction improvement.
- No request-time provider/model/LLM call, raw TWMD output, training, deployment, Track A change or
  GAS/LINE change occurred.
- Audit analysis SHA-256:
  `99d2fa67a7fd32a76fecbc41cfc0c362f40d5cf06979d92a7d9e11a3bfd856c2`.

### F11B-D0 LINE product and multi-user design freeze

- Authoritative design: `docs/f11b_line_product_design_freeze.md`; machine contract:
  `research/configs/f11b_line_integration_design.v1.json`.
- Main menu is exactly 股票分析、持股健檢、金融情報、匯入持股、新聞研究、設定. Reports live
  only under per-user Settings; quota/debug/admin information is hidden from ordinary users.
- Stock, portfolio and intelligence Flex field order, Traditional Chinese limitations and Track
  A/B claim boundaries are frozen.
- Roles are UNREGISTERED, REGISTERED and ADMIN; all private state is keyed by internal user UUID.
- LINE ID, allowlist/shared challenge and F10 `X-User-ID` are not public authentication. Production
  requires a raw-body/header-capable LINE signature verification edge; Apps Script header limits
  are acknowledged rather than bypassed.
- GAS is a thin transition adapter; FastAPI owns identity/authorization, portfolio transactions,
  persistence, models, scheduling policy, privacy, audit and idempotency.
- Legacy capability preservation and user-data isolation matrices are complete. F11B-1A routes,
  1B controlled-demo flow, F11B-2 gate and immutable rollback boundary are frozen.
- No live/migration-copy GAS edit, webhook/trigger/Sheet/holdings change, deployment, model change,
  secret access or external provider call occurred.

### B2 normalized dataset and update contract

- B2 report: `research/evaluation/b2_taiwan_financial_text_dataset_result.md`.
- Authoritative long-term contract: `docs/b2_data_acquisition_and_update_contract.md`.
- Machine config: `research/configs/b2_taiwan_financial_text.v1.json`.
- Schema/builder/idempotency implementation: `pipelines/news/b2_dataset.py`.
- TPEx official CSV provider: `pipelines/news/tpex_material.py`.
- Private ignored dataset: `.tools/datasets/b2-taiwan-financial-text-v1/`, 6,021 FSC documents,
  approximately 27 MB; semantic SHA-256
  `26489f31ca27e2541c09da5dda86af0cb597c989efeb138a14f66a9f18bdab11`.
- No sentiment/impact labels or invented ticker mappings exist in the snapshot.
- TPEx bounded probe passed 65/65 logical rows and nine required fields; response remained in
  system temp storage only.
- GDELT max-25 metadata probe stopped on an expired server TLS certificate; verification was not
  bypassed and zero rows were accepted. B2 v1 therefore uses the official-and-domain fallback
  dataset while retaining the GDELT metadata contract for a future valid extraction.
- TWSE/TPEx remain forward streams; zero baseline rows are explicit and do not imply historical
  no-news observations.
- No 30/90-day, 126-session or six-month wait is required. Scheduled collection does not trigger
  automatic retraining.

### Preserved detailed source findings

- **FinMind `TaiwanStockNews`: CONDITIONAL for deduplicated title-level intelligence; HOLD for
  market-reaction weak supervision and rich-text modeling.** The 2018–2024 ten-ticker stratified
  audit made 280 successful requests and observed 1,547 rows. Sampled 2018–2019 were empty,
  descriptions were absent, timestamps were timezone-naive/semantically undocumented, exact-link
  duplicates were 25.21% and exact-title duplicates were 20.49%. Raw responses remain only in
  ignored `.tools/` storage.
- **TWMD major-event taxonomy: `ACCEPT_SECONDARY` after bounded Pro re-audit.** The earlier
  2018/2022/2024 HTTP 402 result remains preserved as diagnostic history. On 2026-08-29 the active
  Pro key authenticated and returned two 2330 rows from both 2018 and 2024 with ticker, market,
  event date/time, verbatim subject, inferred event class/confidence and rule version. The API has
  a documentation/runtime filter-name mismatch, no encoded timezone and no full body. Company-news
  probes returned zero rows; legacy material information returned 404; private-beta MOPS was not
  entitled. B2 v1 remains unchanged, and TWMD is forbidden from B3 until a separately approved
  versioned B2.1/B2-v2 contract gate passes.
- The TWMD key, if retained locally, belongs only in ignored `.env`. The public `.env.example`
  contains an empty variable name, never a value.
- **eLAND remains `HOLD / excluded from active modeling` and permanently excluded from active
  work.** The later TWMD secondary acceptance does not reactivate eLAND.

## FROZEN F-SERIES RECORD AND CURRENT PRODUCT STATUS

- **F1:** protocol/config/schema/safety-test freeze — planning scope complete.
- **F2:** historical continuous dataset rebuild — complete.
- **F3:** final target, feature and coverage-bias audit — complete with temporal concentration.
- **F4:** persistence/Ridge/HGB regressors — implementation complete.
- **F5:** nested rolling-origin evaluation and OOF predictions — complete; no final winner selected.
- **F6:** ranking/decile/lift/robustness — complete; no final winner selected.
- **F7:** final research artifact and inference freeze — complete; Ridge alpha 100, not deployed.
- **F8:** Financial NLP Intelligence — complete; abstention-safe contract, no model inference.
- **F9:** optional NLP incremental-value study — not run; non-blocking.
- **F10:** FastAPI/backend integration — complete; local only, not deployed.
- **F11A:** controlled Streamlit dashboard complete; not deployed.
- **F11B:** D0/1A/1B/2A complete; F11B-0 safety copy remains immutable; F11B-2 integration has not
  started because exact feature and training/serving parity remain failed at 6/9 gates.
- **F12:** portfolio finalization complete; homepage, evidence-linked story, architecture, charts,
  controlled screenshots, limitations, installation and consistency checks finalized.

## B1 ARTIFACTS

- Authoritative report: `research/evaluation/b1_source_candidate_audit.md`.
- Frozen decision manifest / B2 whitelist:
  `research/configs/b1_source_candidate_manifest.v1.json`.
- Schema and policy guards: `research/planning/b1_source_audit.py`.
- Contract tests: `tests/unit/test_b1_source_audit.py`.
- B1 performed official-documentation web research only: no API/data probe, article fetch, bulk
  download, model training, pseudo-labeling or manual labeling.

## B2 ARTIFACTS

- Contract: `docs/b2_data_acquisition_and_update_contract.md`.
- Result: `research/evaluation/b2_taiwan_financial_text_dataset_result.md`.
- Config: `research/configs/b2_taiwan_financial_text.v1.json`.
- Builder/schema: `pipelines/news/b2_dataset.py`.
- TPEx provider: `pipelines/news/tpex_material.py`.
- CLI: `jobs/b2_dataset.py` / `financial-ai-b2-dataset`.
- Tests: `tests/unit/test_b2_dataset.py` and `tests/unit/test_twse_news_providers.py`.
- The local normalized snapshot is ignored; no raw/provider/corpus text is tracked.

No longer blocking: M12 six-month wait, a new untouched holdout, binary classifier success,
regime-threshold deployment, validated Chinese sentiment, positive NLP lift, TEJ/AP11 or trading
profitability. AP11 is optional; no standalone committed AP11/TEJ source-audit report was found in
R0, so historical wording must not imply that such evidence exists.

## F1 ARTIFACTS

- Plan: `PROJECT_PLAN.md`.
- Protocol: `docs/final_volatility_surprise_study_protocol.md`.
- Migration map: `docs/final_study_migration.md`.
- Machine config: `research/configs/final_volatility_surprise_study.v1.json`.
- Config schema/guards: `research/planning/final_study_protocol.py`.
- Safety tests: `tests/unit/test_final_study_protocol.py`.
- Canonical F1 config SHA-256:
  `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66`.

## F2 ARTIFACTS

- Builder: `pipelines/features/final_study_builder.py`.
- CLI: `jobs/final_study_dataset.py` / `financial-ai-final-study-dataset`.
- Safety tests: `tests/unit/test_final_study_dataset_builder.py`.
- Public result: `research/evaluation/f2_historical_dataset_result.md`.
- Local dataset: `.tools/datasets/final-volatility-surprise-dataset-v1/dataset.json`.
- Dataset SHA-256:
  `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`.

## F5 ARTIFACTS AND RESULT

- Evaluation config: `research/configs/final_nested_temporal_evaluation.v1.json`.
- Evaluator: `research/modeling/final_temporal_evaluation.py`.
- CLI: `jobs/final_temporal_evaluation.py` / `financial-ai-final-temporal-evaluation`.
- Safety tests: `tests/unit/test_final_temporal_evaluation.py`.
- Public result: `research/evaluation/f5_nested_temporal_evaluation_result.md`.
- Local immutable OOF: `.tools/evaluation/f5-final-regression-oof-v1/predictions.json`.
- Canonical F5 config SHA-256:
  `3ebf45f6054d40724970f1be2f1c0bbf6588cb085b7bafe0196077cc304256af`.
- Canonical OOF SHA-256:
  `b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7`.

Seven folds produced 20,637 unique historical evaluation rows and 61,911 three-model OOF
predictions. Mean outer Spearman was 0.0608 for persistence, 0.1940 for Ridge and 0.1863 for HGB.
Ridge and HGB are inside the frozen 0.01 practical-tie margin. Their average R-squared values were
near zero/slightly negative, so the current evidence supports a modest ranking signal more than
accurate magnitude prediction. F5 intentionally selected no final model.

## F6 ARTIFACTS AND RESULT

- Analysis config: `research/configs/final_ranking_robustness.v1.json`.
- Analyzer: `research/evaluation/final_ranking_robustness.py`.
- CLI: `jobs/final_ranking_robustness.py` / `financial-ai-final-ranking-robustness`.
- Safety tests: `tests/unit/test_final_ranking_robustness.py`.
- Public result: `research/evaluation/f6_ranking_robustness_result.md`.
- Local aggregate analysis: `.tools/evaluation/f6-final-ranking-robustness-v1/analysis.json`.
- Canonical F6 config SHA-256:
  `d860f42a3e47d8b136d93a652be6952de786bcdd5cfd94131b7069967ce9c939`.
- Canonical F6 analysis SHA-256:
  `8fd2fdc84f65fb47b6bc87df4b662c4bbd5a9ec8c82d41de4cdd3825b6364e70`.

Ridge/HGB mean top-decile lift was 1.354/1.361 and mean Spearman was 0.194/0.186. Both candidates
had positive ranking and lift above one in every outer period, ticker and training-defined regime.
Their pooled outer-assigned deciles were 9/9 non-decreasing, but individual folds reached only 5–9
steps and the model-level bootstrap intervals overlap. F6 did not select a final model.

## F7 ARTIFACTS AND RESULT

- Freeze config: `research/configs/final_model_freeze.v1.json`.
- Model/inference implementation: `research/modeling/final_research_model.py`.
- CLI: `jobs/final_model_freeze.py` / `financial-ai-final-model-freeze`.
- Safety tests: `tests/unit/test_final_research_model.py`.
- Public result: `research/evaluation/f7_final_research_model_result.md`.
- Local safe JSON artifact: `.tools/models/f7-final-ridge-research-v1/model.json`.
- Canonical F7 config SHA-256:
  `d87b335e3a03382ca7f0e45bb80fdb862e9017b93756a40171d61936410dc167`.
- Canonical model artifact SHA-256:
  `279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de`.

Ridge/HGB were a practical tie under the frozen 0.01 Spearman margin. Ridge was selected by the
first applicable tie-break, lower mean outer MAE. Temporal validation over 2023/2024/2025 selected
alpha 100. The final research fit used all 32,357 eligible rows and persisted scaler/model state plus
20,637 Ridge OOF reference scores as safe JSON. It was not deployed and makes no prospective claim.

## F8 ARTIFACTS AND RESULT

- Frozen config: `research/configs/financial_nlp_intelligence.v1.json`.
- Contract assembler: `pipelines/intelligence/financial_nlp.py`.
- CLI: `jobs/financial_nlp_intelligence.py` / `financial-ai-nlp-intelligence`.
- Safety tests: `tests/unit/test_financial_nlp_intelligence.py`.
- Public result: `research/evaluation/f8_financial_nlp_intelligence_result.md`.
- Local aggregate analysis: `.tools/evaluation/f8-financial-nlp-intelligence-v1/analysis.json`.
- Canonical F8 config SHA-256:
  `de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4`.
- Canonical F8 analysis SHA-256:
  `8994a66e2fef70da2ad16d54cb3698ac8e2f14badad4e9237a03e2669b97ab42`.

Seven historical NLP evidence files passed byte-hash verification. English text is either scored
with the exact pinned FinBERT revision or remains `ELIGIBLE_NOT_SCORED`; Chinese/Taiwan polarity
always abstains with null probabilities. Official metadata and deterministic event/impact proxies
are separate from sentiment and are not ground truth. The controlled audit ran no model, API, LLM,
manual review, training or deployment, and persisted no fixture rows/private text.

## F10 ARTIFACTS AND RESULT

- Frozen config: `research/configs/backend_integration.v1.json`.
- Config guards: `research/planning/backend_integration.py`.
- Prediction service: `backend/app/services/research_prediction.py`.
- Intelligence service/repository: `backend/app/services/intelligence.py` and
  `backend/app/repositories/intelligence.py`.
- API/schema: `backend/app/api/research.py` and `backend/app/schemas/research.py`.
- Audit CLI: `jobs/backend_integration.py` / `financial-ai-backend-integration`.
- Tests: `tests/unit/test_backend_integration_protocol.py` and
  `tests/integration/test_research_api.py`.
- Public result: `research/evaluation/f10_backend_integration_result.md`.
- Canonical F10 config SHA-256:
  `b4367815b484352375b6693d91b44298b8e4dc3b84bf0a3c69f956f97175a4f2`.
- Canonical F10 analysis SHA-256:
  `dc26d6f13e07c27e8ec32b6da8d06ac6fb1fed9b5fff32040a9d69221394b5fb`.

The POST prediction endpoint validates the exact 23-feature F7 contract and returns score,
percentile, band and lineage. The GET intelligence endpoint reads only stored news/ticker/pinned
English sentiment rows and preserves Chinese abstention. F10 makes no external request, trains no
model, exposes no private portfolio data, modifies no GAS and performs no deployment. F9 was not
run and no NLP-lift claim exists.

## PRIVATE GAS / LINE HANDOFF

Status: **working private prototype; immutable backup/migration copy verified; live behavior
unchanged; F11B integration pending**.

Authoritative private inputs inspected:

- `/Users/xander/Desktop/code.gs`;
- `/Users/xander/Desktop/appsscript.json`.

They are not repository artifacts and must not be copied into this public/research repository.
`gas_legacy/README.md` remains a warning-only placeholder; `line_adapter/` remains a transitional
boundary, not a deployed integration.

The user now authorizes future Codex modification of the **private migration copy**, but only under
`docs/gas_migration_safety_freeze.md`. The sole live/original source must remain recoverable. R0
does not authorize a behavioral edit or deployment.

R0 backup state:

- immutable source: `.tools/private/gas-migration/r0-20260829/immutable-original/` (`0400`);
- migration copy: `.tools/private/gas-migration/r0-20260829/migration-copy/` (`0600`);
- both `code.gs` and `appsscript.json` matched the Desktop originals by `cmp` and SHA-256;
- `.tools/` is Git-ignored; no private source or identifier was added to the public repository.

### Existing GAS functions to preserve at product level

- LINE `doPost` webhook routing for follow, text and image events;
- authorized-user allowlist and per-user temporary state in Script Properties;
- LINE reply/push and Flex Message menu, portfolio, report, alert, help and quota cards;
- Gemini-based text/broker-screenshot extraction with confirmation before writing holdings;
- single-row add/update and full portfolio synchronization in Google Sheets;
- holdings freshness warning and last-update timestamp;
- Yahoo chart lookup for `.TW`/`.TWO`, current price, daily change, ROI, 5-day and 20-day averages;
- portfolio cards, stop-profit/stop-loss alerts, morning and afternoon report entry points;
- Perplexity on-demand news/research with citations;
- usage counters, estimated provider balance and Sheet-based error logging.

The code defines `morningPushReport` and `afternoonPushReport`, but installed Apps Script triggers
are external project state and cannot be proven from `code.gs` or the manifest. Their schedules and
last-run status must be checked manually in Apps Script before migration.

### Current GAS storage and external services

- Script Properties hold the main LINE user/token, Gemini key, Perplexity key and Spreadsheet ID.
- Google Sheets is the live private holdings store and error log.
- A legacy source-backup helper writes project source into a Google Doc.
- External calls include LINE Messaging/Data APIs, Gemini, Perplexity, Yahoo Finance and Google
  Apps Script/Drive/Docs/Sheets services.
- The manifest uses V8, `Asia/Taipei`, broad Script/Docs/Drive/Sheets/external-request scopes and an
  anonymously reachable web-app deployment executed as the deploying user.

### GAS security and correctness risks

- The webhook handler does not verify a LINE request signature and processes only the first event.
- Anonymous web-app access is combined with an allowlist plus a hard-coded shared challenge; this
  is not adequate public authentication.
- Mutating `EXECUTE|...` and `SYNC|...` commands carry holdings fields inside LINE message text and
  are not cryptographically bound to a preview, user, expiry or one-time nonce.
- Full synchronization clears Sheet rows before rebuilding them and uses no `LockService`, database
  transaction or idempotency key; concurrent/replayed events can corrupt holdings.
- The legacy file still contains hard-coded Google resource IDs in backup/authorization helpers.
  Do not copy them, and move them to private configuration if those helpers remain.
- Real holdings, cost basis and broker screenshots are sent to external AI services in the private
  prototype. This is incompatible with the controlled public research edition.
- Perplexity prompts currently request actionable buy/sell guidance, which conflicts with the final
  research-only/non-investment-advice claim boundary.
- Provider calls, Sheet access, presentation, persistence and orchestration are coupled in one large
  file; retries can repeat side effects and error logs may retain excessive provider details.
- Credential rotation after any historical exposure was user-reported previously but is not
  independently verifiable from source. Never record credential values in this handoff.

### Target GAS architecture

Keep GAS deliberately thin:

```text
LINE webhook
  → minimal event parsing / routing
  → signed, authenticated request to Python backend
  → receive versioned response contract
  → LINE reply / push / Flex rendering
```

Keep in GAS during the transition:

- LINE webhook entry point and reply-token timing;
- minimal command/menu routing;
- Flex Message rendering and scheduled push trigger entry points;
- only secrets strictly required for LINE and backend authentication, stored in Script Properties.

Move to Python/FastAPI:

- verified LINE signature processing and identity mapping;
- portfolio validation, preview/confirm, idempotency, transactions and persistence;
- screenshot/OCR orchestration and privacy controls;
- market/news ingestion, price features, NLP/LLM use, F7 inference and intelligence retrieval;
- scheduling, retries, quotas, observability and audit logs;
- all research claims, lineage, model versions and abstention rules.

Do not connect the current GAS directly to F10 yet. F10 is local/research-only, the prediction
endpoint requires an exact 23-feature vector, the intelligence endpoint performs no live fetch,
and production authentication/rate limiting/deployment are not implemented. The current
`X-User-ID` portfolio contract is development-only and must never be treated as public auth.

### Safe F11B migration sequence

1. **F11B-0:** immutable backup/migration copy — safety prerequisite completed in R0; trigger and
   deployment IDs/schedules remain unknown because they are not present in the supplied files.
2. **F11B-1A:** add only new `risk`/`intel`/optional `news` routing in the migration copy; do not
   alter holdings, Sheet schema, screenshot writes, legacy commands or schedules.
3. **F11B-1B:** use deterministic fixture or stored validated snapshot and visibly label
   `CONTROLLED RESEARCH DEMO`.
4. **F11B-2:** current-market inference only after audited OHLCV/TAIEX, exact 23-feature parity,
   cutoff/timezone/missing-data lineage and separate validation.
5. Portfolio-write migration remains later work and must not be used as the first integration step.

Do not deploy, change the live webhook/trigger schedule or edit live holdings without the
corresponding future milestone instruction and rollback verification.

## SAFETY AND NEXT ACTION

Do not rewrite F5/F6/F7/F8/F10 evidence, retune the frozen Ridge from subgroup results, rerun M7,
fabricate Chinese sentiment, create a fake sealed test, modify working GAS, deploy, commit or push
during the R0 stop boundary. Do not start B1 automatically.

Run and preserve automated checks for random-split prohibition, exact next session, `t+1` mutation,
rolling shift, target-field exclusion, duplicate ticker/date, inner/outer isolation, fold-local
preprocessing and exact hashes.

F3 found no ticker or known-volatility-regime concentration, but calendar years
2012/2013/2016/2017/2019 and outer fold 2017–2018 triggered the predeclared coverage rule. The
warning therefore remains `DATA_LIMITATION_WITH_DETECTED_COVERAGE_CONCENTRATION`; it is not a
target/leakage/code defect. See `research/evaluation/f3_target_feature_coverage_audit_result.md`.

F4 implemented 1 persistence, 4 Ridge and 16 HGB parameterized candidates under the frozen F1
grid. Synthetic tests confirm training-only scaling, temporal-overlap rejection and deterministic
fit manifests/predictions. See `research/evaluation/f4_regression_candidates_result.md`.

## F11A ARTIFACTS AND RESULT

- Dashboard：`demo/app.py`。
- Strict contracts／safe API client／presentation：`demo/contracts.py`、`demo/client.py`、
  `demo/presentation.py`。
- Deterministic builder／controlled fixture：`demo/fixture_builder.py`、
  `demo/fixtures/controlled_dashboard_demo.v1.json`。
- Frozen config：`research/configs/dashboard_demo.v1.json`。
- Tests：`tests/unit/test_dashboard_demo.py`、`tests/unit/test_dashboard_client.py`、
  `tests/integration/test_streamlit_dashboard.py`。
- Public result：`research/evaluation/f11_dashboard_demo_result.md`。
- Canonical config SHA-256：
  `0f70c88b6ea3b6e21177ae2fce6a4bef17d1b02a89a0dd7d491d425663ebc267`。
- Canonical fixture SHA-256：
  `c55f546ebe9ee94f616d518c205c18acb6b35683436dce1a312e7849c2935c06`。

F11A 預設完全離線且只顯示合成資料；本機 API 模式限 plain-HTTP loopback origin。合成分數由
frozen F7 artifact 產生，但不是實際 2330 觀測或 performance evidence。中文 polarity 維持
abstain，英文範例維持 eligible-not-scored。未修改 GAS、未部署、未呼叫 provider/LLM。

F11A 展示內容包括：next-session relative volatility-surprise score、歷史 percentile、
LOW/MODERATE/HIGH/VERY HIGH communication band、合成 feature context、近期 intelligence、
lineage 與研究／非投資建議聲明。它不是持股 Dashboard，也不顯示真實個資。

本機啟動：

```bash
python -m pip install -e ".[dev,demo]"
streamlit run demo/app.py
```

若要使用 `LOCAL_API` 模式，另開終端執行 `uvicorn backend.app.main:app --reload`。F10 提供：

- `POST /api/v1/research/volatility-surprise/predict`；
- `GET /api/v1/research/intelligence/{ticker}`；
- `GET /health`。

Dashboard client 只接受帶明確 port 的 `http://127.0.0.1`、`http://localhost` 或
`http://[::1]`，拒絕外部 host、credentials、path、query 與 fragment。

## R0 GIT / AUDIT SNAPSHOT

Commit `d397cdf` already tracks B1 and, through its parent history, R0 plus:

- FinMind audit files:
  `research/configs/finmind_news_longitudinal_audit.v1.json`,
  `research/evaluation/finmind_news_longitudinal_audit.py`,
  `research/evaluation/finmind_taiwan_stock_news_longitudinal_audit.md`,
  `tests/unit/test_finmind_news_longitudinal_audit.py`;
- historical TWMD HOLD/probe files:
  `research/configs/twmd_major_event_probe.v1.json`,
  `research/evaluation/twmd_major_event_probe.py`,
  `tests/unit/test_twmd_major_event_probe.py`;
- the related `.env.example`, `pyproject.toml` and Taiwan source-decision updates.

The current uncommitted work contains the F11B-1B FastAPI controlled endpoint, HMAC service-auth,
schemas/service/tests/documentation and ignored private migration-copy integration. Exact worktree
state must be taken from final `git status`. No automatic commit or push is authorized.

Ignored local-only files include FinMind raw audit cache, the TWMD probe output/cache, model/eval
artifacts and `.env`. Never add them with a forced Git add.

Most recent validation including F11B-D0:

- full project suite: 282 tests passed (2 dependency/environment warnings only);
- full Ruff check, `git diff --check` and repository secret scan passed;
- historical TWMD entitlement result: 2018/2022/2024 all HTTP 402, zero accepted rows.

Latest bounded Pro re-audit superseding operational source status:

- authentication confirmed without recording the key;
- major-event taxonomy HTTP 200 with two bounded 2330 rows in each of 2018 and 2024;
- issuer-classification helper HTTP 200;
- company-news HTTP 200 but zero rows in 2018, 2024 and the documented 2026 sample date;
- legacy material-information HTTP 404; private-beta MOPS not entitled;
- final classification `ACCEPT_SECONDARY`, B2 v1 unchanged; completed B3 used zero TWMD rows.

No automatic commit or push is authorized.

F11B-1B is complete and not deployed. F11B-2A supersedes the earlier 2/9 snapshot: official TWSE
coverage, TAIEX, cutoff, missingness, timezone and lineage now pass, for 6/9. Exact 23-feature and
training/inference parity fail because adjusted-price lineage is unresolved and raw-source values
differ; E2E was not run. Decision:
`OFFICIAL_OHLCV_AVAILABLE_BUT_ADJUSTED_PARITY_UNRESOLVED` / `NOT_READY_FOR_F11B_2`. F12 remains
complete. The R1A URL exists, but its first build exposed a nested-entrypoint import error. The
fixed root-path bootstrap passes a cloud-like regression test and awaits user-controlled
commit/push/redeploy. The next suggested unit is R1B only after the corrected HTTPS smoke test.
Track A/B models stay frozen.
