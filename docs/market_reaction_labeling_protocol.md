# Automatic Market-Reaction Labeling Protocol v1

Status: v1 engine implemented; historical train/validation backfill required

## 1. Meaning and claims boundary

`POSITIVE_REACTION`, `NEUTRAL_REACTION` and `NEGATIVE_REACTION` describe observed, automatically
calculated market reactions. They are not linguistic sentiment, human opinion, expert labels or
proof that an event caused a price move.

## 2. Event identity and timestamp

- Primary timestamp: persisted `news_articles.published_at` supplied by the traceable source.
- Store timestamps in UTC and convert with IANA timezone `Asia/Taipei` for market alignment.
- A provider `fact_date` or fetch time must not replace the publication timestamp.
- Missing, timezone-naive or implausible timestamps cause `ABSTAIN_TIMESTAMP`; they are never
  guessed from later prices.
- Exact duplicates, near-duplicate rewrites, corrections and follow-ups share a versioned
  `event_group_id` before any split is created.

## 3. Trading-calendar alignment

- The initial information cutoff is 13:30 Asia/Taipei.
- An event published on an observed trading day at or before 13:30 maps to that session.
- An after-cutoff, weekend or non-trading-day event maps to the next observed trading session.
- Final implementation must reconcile observed price dates with an audited exchange calendar.
  A weekday gap is not automatically treated as a holiday and is never forward-filled silently.
- `effective_session` is the first session allowed to reflect the event under these rules.

## 4. Reaction windows

With daily adjusted-close data:

- `anchor_session`: the observed session immediately before `effective_session`.
- `next_session` / `1d`: adjusted close from `anchor_session` to `effective_session`.
- `3d`: adjusted close from `anchor_session` to the third observed session beginning with
  `effective_session`.

The exact horizon definition is stored in every row. If intraday prices are later introduced, they
require a new protocol version rather than silently changing v1.

## 5. Benchmark and formulas

The benchmark is a versioned, broad Taiwan-market series selected in configuration and aligned to
the same currency, source quality contract and sessions as the stock.

For horizon `h`:

```text
raw_return_h       = adjusted_close_stock(end_h) / adjusted_close_stock(anchor) - 1
benchmark_return_h = adjusted_close_benchmark(end_h) / adjusted_close_benchmark(anchor) - 1
abnormal_return_h  = raw_return_h - benchmark_return_h
```

A market-model residual may be evaluated later, but its beta and estimation window must be fit on
training history only and must use a new formula/version identifier.

## 6. Reaction classes and neutral band

For a symmetric neutral threshold `tau_h`:

```text
abnormal_return_h >  tau_h  → POSITIVE_REACTION
abnormal_return_h < -tau_h  → NEGATIVE_REACTION
otherwise                    → NEUTRAL_REACTION
```

- Candidate fixed thresholds and train-derived quantiles may be compared on training/validation.
- Thresholds, class balancing, beta, scaling and neutral-band width must never use the final test.
- Once selected, the configuration is frozen and applied unchanged to the sealed test.
- Reports include the continuous returns so classification thresholds remain auditable.

## 7. Corporate actions and missing prices

- Use the versioned adjusted-close series and retain its snapshot hash.
- Material provider revisions create a new market snapshot; historical labels are not overwritten.
- Missing anchor, end or benchmark observations cause an explicit missing reason and abstention.
- Do not interpolate, forward-fill or substitute unadjusted prices without a new audited policy.
- Suspected corporate-action anomalies are quarantined by automated quality rules.

## 8. Multiple events and duplicate news

- Multiple same-ticker disclosures assigned to one effective session form one
  `ticker_session_information_set` when causal attribution is not identifiable.
- The same reaction can be attached to the information set for prediction research, but must not be
  presented as the causal impact of each individual article.
- Exact and near-duplicate articles contribute once per event group.
- An event group may belong to only one chronological split.

## 9. Leakage protections

Automated tests must cover:

- publication timestamp and timezone leakage;
- before/after-cutoff and non-trading-day alignment;
- mutation of future prices changes targets but not event-time features;
- rolling calculations end at the information cutoff and are shifted when required;
- train/validation/test split boundaries precede threshold/model selection;
- exact, fuzzy and same-event duplicates cannot cross splits;
- reaction-derived prediction features use only older events whose complete reaction window ended
  before the current prediction timestamp.

Future market reaction may be used only as a historical training target, weak label, evaluation
outcome or past-completed statistic. It is forbidden as an input for the event being predicted.

## 10. Planned record contract

Each `market_reaction_labels` row records:

- article/event-group ID, ticker and source publication timestamp;
- timezone, information cutoff, effective/anchor/end sessions and horizon;
- raw, benchmark and abnormal returns;
- continuous threshold inputs, reaction class and abstention/missing reason;
- benchmark ID, market snapshot hash, split assignment and protocol version.

## 11. M8 implementation evidence and current boundary

The v1 engine, FinMind TAIEX benchmark adapter, per-ticker Yahoo ingestion job and immutable
split-separated JSONL builder are implemented. The first bounded run used 108 deduplicated official
TWSE events, 599 stock-price rows and eight benchmark sessions. It emitted 324 horizon rows. All
events fall in the predeclared sealed-test period, so train and validation contain zero rows.

The builder therefore reports `implementation_complete_historical_backfill_required`, withholds
test return/class statistics, and forbids downstream training or threshold selection from this
snapshot. This run proves the calculation and lineage path, not predictive value or dataset
readiness. A separately audited historical official-event source must populate non-empty train and
validation periods before M11 can consume reaction targets. The ignored machine-readable report is
`artifacts/m8-market-reaction-build-report.json`; generated prices, benchmark rows and targets stay
under ignored local storage.
