# Architecture

## Active research direction

The core research path is now next-session abnormal-volatility / large-move risk prediction from
leakage-safe price, volume, volatility, technical and market-context features. Financial NLP is a
separate intelligence layer and optional ablation, not a dependency for core completion. The
existing ingestion, portfolio, English sentiment and exploratory Taiwan NLP boundaries below are
preserved and reusable; their historical milestone numbers are mapped in
`docs/research_direction_migration.md`.

## Active Track A M1–M3 boundary

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
```

M2 never substitutes a later provider row for a missing immediate exchange session. Threshold fit
requires `t` and `t+1` inside training; validation is materialized but not used to fit the target
threshold. Sealed-test outcomes/labels remain unmaterialized until M7. Detailed provider and label
rows stay in ignored local storage.

M3 keeps the `features` mapping structurally separate from the target object, verifies M2's
feature-state commitment, and refuses gaps in its fixed 35-session lookback. It fits no
preprocessing and materializes no sealed-test feature.

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

`X-User-ID` exists only to exercise ownership during the transition. It must not be exposed as standalone authentication. M10 replaces it with identity derived from a verified LINE webhook or another authenticated service boundary.

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
