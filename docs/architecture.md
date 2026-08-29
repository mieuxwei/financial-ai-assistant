# Architecture

## Final portfolio architecture

![Financial AI Assistant architecture](assets/system_architecture.svg)

F12 is complete as a documentation and controlled-demo milestone. R1A adds a public-release
boundary around the F11A presentation layer:

```text
Public browser → Streamlit Community Cloud → demo/public_app.py → synthetic fixture only
```

The R1A path requires no FastAPI, database, provider, model artifact or runtime secret. It is ready
for manual deployment but has no public URL yet. F11B-2 current-market serving remains blocked
after F11B-2A because exact feature parity is 5/23 and the audited official corporate-action
lineage cannot reproduce the historical Yahoo `adjclose` contract.

The final ownership boundary is:

- FastAPI/Python owns identity, portfolio rules, persistence, data pipelines, Track A/B contracts,
  lineage, abstention and auditability;
- Streamlit presents a deterministic controlled fixture or an explicitly selected loopback API;
- GAS remains a transitional thin LINE adapter and does not own model or portfolio logic;
- provider calls never occur inside the controlled demo request path;
- live/current inference must remain unavailable until every frozen serving gate passes.

## Active research direction

The active final-study path is continuous next-session stock-normalized volatility-surprise
forecasting from leakage-safe price, volume, volatility, technical and market-context features.
Financial NLP is a parallel intelligence layer and an optional timestamp-safe incremental-value
experiment, not a dependency for core completion. The research model returns a continuous score;
LOW/MODERATE/HIGH/VERY HIGH are presentation bands fitted from historical development evidence,
not classifier labels.

The canonical active contracts are:

- `research/configs/final_volatility_surprise_study.v1.json`;
- `docs/final_volatility_surprise_study_protocol.md`;
- `docs/final_study_migration.md`.

The existing ingestion, portfolio, English sentiment and exploratory Taiwan NLP boundaries below
remain reusable. The binary M1–M11 architecture is preserved immediately below as immutable
exploratory research history; it is not the final production-research model.

## Final-study boundary (F1–F12 complete as a research portfolio)

```text
immutable historical market data + source lineage
  → feature-date / target-session / information-cutoff dataset snapshot
  → t-known compact market feature vector
  → next-session absolute log return
       / t-only trailing 20-session stock volatility
  → expanding-window outer evaluation
  → inner temporal model/hyperparameter selection
  → persistence + Ridge + HistGradientBoosting comparison
  → outer-fold OOF scores and regression/ranking evidence
  → frozen research model + percentile communication bands
  → FastAPI / LINE presentation with Financial NLP intelligence
```

Every fold refits preprocessing from its own training history. No random split, global
preprocessing, future target feature, outer-fold tuning or relabelled historical sealed test is
allowed. Previously inspected 2025–2026 rows may be historical outer evaluation periods, but are
not described as untouched or prospective evidence.

## Exploratory binary-risk architecture (historical M1–M11; frozen)

```text
fixed universe + Yahoo OHLCV + FinMind TAIEX
  → immutable M1 market snapshot + quality audit
  → exact benchmark-session alignment
  → t-known 20-session volatility scale
  → train/validation next-session continuous outcomes
  → training-only 90th-percentile candidate threshold
  → NORMAL / HIGH_RISK labels + immutable hashes
  → 35-session t-only market feature window
  → 23 price / volume / volatility / technical / TAIEX features
  → immutable train/validation risk-feature dataset
  → training-only StandardScaler + Logistic Regression
  → validation-only baseline metrics and calibration bins
  → fixed Random Forest + HistGradientBoosting comparison
  → validation permutation importance + resource evidence
  → five expanding-window evaluations
  → prequential Platt calibration + recall-constrained threshold
  → frozen pre-test candidate manifest
  → one-time immutable sealed-test evaluation
  → read-only robustness/error analysis with pre-test-fit regimes
  → session-cluster bootstrap uncertainty and raw-free M8 report
```

M2 never substitutes a later provider row for a missing immediate exchange session. Threshold fit
requires `t` and `t+1` inside training; validation is materialized but not used to fit the target
threshold. Sealed-test outcomes/labels remain unmaterialized until M7. Detailed provider and label
rows stay in ignored local storage.

M3 keeps the `features` mapping structurally separate from the target object, verifies M2's
feature-state commitment, and refuses gaps in its fixed 35-session lookback. It fits no
preprocessing and materializes no sealed-test feature.

M4 fits the scaler, balanced class weights, and Logistic Regression only from training rows.
Historical prevalence and previous-period persistence provide naive comparisons. Validation is
read only to calculate metrics; it does not tune the fixed 0.5 threshold or any model parameter.
The learned model is a versioned JSON artifact in ignored local storage. Sealed-test features and
outcomes remain unopened.

M5 fits both tree models directly on the same unscaled M3 training matrix. HGB internal early
stopping is disabled so it cannot create an implicit validation carve-out. Fixed-seed validation
permutation importance is evaluation evidence only and is not used to refit or select features.
The first parallel Random Forest diagnostic exposed non-identical floating-point prediction hashes;
the accepted configuration is single-threaded and passes repeated immutable reconstruction.

M6 trains each fold only on rows whose next-session target finishes before that fold's evaluation
period. Calibration for a fold is fit only from earlier out-of-fold predictions. Candidate model,
calibration method and threshold are selected from pre-test evidence, after which the final recipe
is fit through 2024 and frozen. The manifest contains no test row or test metric; M7 must verify its
hash before the single authorized sealed-test opening.

M7 now owns a three-record boundary: opening intent, immutable row-level evaluation in ignored
storage, and completion record. The opening record is created before test data are loaded; its
existence makes every future execution fail before evaluation. Public documentation contains only
aggregate evidence. M8 must analyze the existing evaluation artifact and may not reconstruct or
rerun M7.

M8 verifies that chain before reading rows, derives volatility-regime cutoffs only from the
pre-test feature dataset, and writes aggregate ticker/time/regime/probability/error summaries. It
does not expose rows, refit the model or feed subgroup results back into Track A. Post-M8 M9–M13
test new conditional/operating-policy hypotheses under a separate frozen protocol; the NLP
intelligence layer moves to M14.

M9 has now completed the first post-M8 diagnostic without changing the prediction boundary. The
raw outcome reversal disappears after common stock-volatility-regime standardization, supporting a
stock-normalized surprise interpretation. M10 remains a separate development-only policy layer and
may not read M7/M8/M9 labels or outcomes for threshold selection.

M10 materializes a private, immutable development OOF dataset only under `.tools/`. It reconstructs
fold Logistic/Platt evidence and stops before M6 final fit. Selected global policies remain an
offline development-policy layer; only M12 can authorize a future product operating-mode contract.

M11 consumes that same immutable OOF dataset without reconstructing or fitting another model. Each
walk-forward fold receives LOW/MIDDLE/HIGH state from trailing stock volatility and tertiles fitted
only on its earlier training history. The selected 0.12/0.10/0.08 decision layer reduces operating
dispersion but lowers overall MCC; it remains offline until a new M12 holdout exists.

## Legacy first-iteration application boundary

The M0–M2 implementation establishes FastAPI, SQLAlchemy/Alembic, user-owned portfolios, and atomic portfolio synchronization. It deliberately does not implement market data, news, sentiment, models, or backtesting.

```text
Transitional trusted caller
  → X-User-ID context
  → FastAPI portfolio API
  → PortfolioService
  → SQLAlchemy repository
  → SQLite (local) / PostgreSQL (deployment target)
```

`X-User-ID` exists only to exercise ownership during the transition. It must not be exposed as standalone authentication. M18 replaces it with identity derived from a verified LINE webhook or another authenticated service boundary.

Portfolio sync uses a short-lived preview operation. Confirm applies additions, updates, and removals in one database transaction and is idempotent.

## Planned system

Future ingestion pipelines will remain separate from feature generation and offline research. The LINE adapter consumes backend contracts and must not become a second source of portfolio, market-data, or research truth.

## M3 market-data boundary

```text
Universe config
  → MarketDataRequest (canonical ticker + provider symbol)
  → MarketDataProvider protocol
  → YahooFinanceProvider
  → schema parsing + Taipei trading-date normalization
  → quality assessment
  → transactional SQLAlchemy upsert
  → market_prices / market_ingestion_runs
  → deterministic snapshot + SHA-256
```

Canonical tickers are independent of `.TW` or `.TWO`; provider symbols live in configuration. Provider response parsing, retry policy, data-quality assessment, persistence, and snapshot generation are separate modules so Yahoo can be replaced without changing research contracts.

## M4 news boundary

```text
TWSE material-announcement OpenAPI ─┐
                                    ├→ NewsItem contract
TWSE official news RSS ─────────────┘
  → URL/title normalization
  → exact hash + fuzzy title deduplication
  → official-code / configured-alias ticker matching
  → transactional news_articles + article_tickers
  → news_ingestion_runs audit record
```

Provider adapters never call Perplexity or another LLM. The OpenAPI provider uses the official company code as an explicit match and its stable record identity for exact deduplication; distinct official records are not collapsed merely because their titles resemble one another. RSS matching is deterministic and records its method and score. Raw RSS HTML and full article bodies are discarded after extracting a maximum 500-character plain-text excerpt. Source URL, timestamps, external identifier and provider metadata preserve traceability.

## M5 sentiment boundary

```text
news_articles + article_tickers
  → explicit language gate (English only for ProsusAI/finbert)
  → title + legal short summary input contract
  → fixed model ID + immutable revision
  → batched CPU inference
  → positive / neutral / negative + continuous score
  → sentiment_results
  → Asia/Taipei calendar-day aggregation
  → daily_sentiment_aggregates
```

The model adapter is optional and lazy-loaded, so FastAPI and CI do not download PyTorch or model weights. Results are keyed by article, ticker and model version. Inference runs record scored, existing and unsupported-language counts; unsupported text is never silently converted to neutral. M6 will decide trading-session attribution and information cutoffs—M5 daily dates are calendar-day aggregates only.

## M6 feature-dataset foundation

```text
market_prices ───────────────────────────────┐
                                             ├→ immutable FeatureConfig
news_articles + article_tickers             │   → trading-session cutoff assignment
  + pinned sentiment_results ───────────────┘   → trailing-only technical/sentiment features
                                                 → next-session return + Up/Down label
                                                 → daily_features
                                                 → feature_dataset_runs + SHA-256 snapshot
```

The information cutoff is Asia/Taipei 13:30 for the first Taiwan-market contract. A publication at or before the cutoff may enter that session; a later, weekend, or holiday publication enters the next observed trading session. Market features end at `t`; only the label reads the adjusted close at the next observed session. Dataset hashes exclude operational UUIDs and timestamps and include the exact configuration and normalized market/sentiment inputs.

M6 currently accepts validated English sentiment and keeps unsupported Chinese probability/score values missing. It is a versioned engineering foundation, not evidence that Taiwan-domain text modeling has been solved.

## Planned zero-manual-label Taiwan NLP and market-reaction boundaries

```text
                                  ┌→ English financial text
news_articles + article_tickers ──┤   → pinned ProsusAI/finbert
                                  │   → sentiment_results
                                  │
                                  └→ accepted/audited Taiwan financial text
                                      ├→ domain-adapted frozen text representation
                                      ├→ official source category (unaltered)
                                      ├→ inferred normalized event type
                                      └→ deterministic / model weak signals
                                          + agreement / entropy / confidence / abstention
                                          → taiwan_text_signals

event timestamp + historical stock/benchmark prices
  → exchange-calendar + cutoff alignment
  → leakage-safe reaction window
  → raw / benchmark / abnormal return + reaction class
  → market_reaction_labels

validated English sentiment ──────┐
Taiwan representation / metadata ├→ versioned integrated dataset
weak-supervision signals ─────────┤   → chronological downstream experiments
past-completed reaction stats ────┤   → walk-forward ablation / backtest
price / volume / technical ───────┘
```

The Taiwan track performs no manual annotation, manual label review or human adjudication. It uses
audited unlabelled domain text, structured official metadata, deterministic rules, versioned weak
supervision and automatically generated market-reaction targets. Official source categories are
stored separately from inferred normalized event types and are never silently rewritten.

The accepted FSC path now builds a checksummed 6,021-record corpus under ignored storage. Splits are
assigned by each document family's latest publication date, so content and family hashes cannot
cross train, validation and sealed test. The M7 feasibility runner reads train/validation only,
pins model revisions and emits resource/loss statistics without saving weights or source text.
The approved bounded pilot subsequently saved two immutable ignored safetensors artifacts. Under
the predeclared identical-vocabulary/final-validation-loss rule, BERT-base-Chinese is the frozen
representation candidate for later ablation; this is not a sentiment classifier decision.

English sentiment, Taiwan text signals and historical market reaction are separate contracts.
Future returns may train or evaluate a reaction model, but never enter a feature available at the
event timestamp. Predictive improvement does not establish linguistic or sentiment correctness.
GAS remains outside these pipelines and only routes LINE interactions to Python during migration.

The M8 implementation stores benchmark snapshots and split-separated reaction targets only under
ignored local paths. Its first bounded input is entirely in the sealed-test interval, so the engine
is operational but the historical dataset is not training-ready. A separately audited official
event backfill must precede threshold fitting and downstream model work.

Active Taiwan source audits prioritize `tw-finance-159M`, MOPS/TWSE, FinMind, optional FSC
regulatory text and historical stock/benchmark prices. Eland is excluded from the active modeling
pipeline and appears only in historical rejection documentation.

## F8 Financial NLP Intelligence boundary

The unified assembler consumes normalized `NewsItem` records plus ticker matches. It may attach a
prediction only for English text and only from the pinned FinBERT revision. Unsupported Chinese
polarity returns explicit abstention and null probabilities; TWSE company/clause/fact-date metadata
and deterministic event/impact cues occupy separate fields and are never treated as sentiment
ground truth. The assembler performs no retrieval, external API call, model inference or LLM
generation itself. This keeps ingestion/model runtimes optional and preserves a deterministic,
testable product contract for later F10 integration.

## F10 research API boundary

```text
validated 23-feature request
  → lazy load + verify F7 safe JSON artifact
  → continuous score + OOF percentile + communication band + lineage

stored news_articles + article_tickers + optional pinned sentiment_result
  → F8 assembler
  → database-only intelligence response with abstention and claim boundaries
```

The prediction endpoint does not build current features in F10; callers must supply the exact
frozen contract. The intelligence endpoint never fetches providers or runs models/LLMs during a
request. Both endpoints are public-research surfaces and exclude portfolio/private data. Existing
portfolio ownership controls remain separate. Artifact absence/tampering fails closed; production
authentication, rate limiting, scheduling and deployment remain outside F10.

## F11A controlled dashboard boundary

```text
controlled synthetic fixture ───────────┐
                                        ├→ Streamlit presentation
loopback-only F10 API (optional) ───────┘   → score / percentile / band
                                             + intelligence / lineage / disclaimers
```

Offline mode is the default and performs no network request. Local API mode accepts only explicit
plain-HTTP loopback origins. The demo excludes holdings/private data and does not fetch providers,
run NLP/LLM inference, modify GAS or deploy. Its fixed synthetic 2330 fixture demonstrates the
interface contract and is not live data or performance evidence.
