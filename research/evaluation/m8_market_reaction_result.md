# M8 Automatic Market-Reaction Labeling Result

Date: 2026-08-26  
Status: engine complete; historical train/validation backfill required

## Result

`market-reaction-v1` is implemented with deterministic Asia/Taipei cutoff alignment,
next-session/1-day/3-day horizons, adjusted stock and TAIEX benchmark returns, abnormal returns,
fixed exploratory neutral bands, chronological splits, explicit abstention and immutable hashes.
Future prices are target-side only. No manual labels, manual review, event text, private holdings or
sentiment ground truth are stored in the generated target files.

The bounded run used:

- 115 official TWSE article-ticker links, collapsed to 108 event groups;
- 599 Yahoo adjusted-price rows for 75 tickers;
- eight FinMind `TaiwanStockTotalReturnIndex:TAIEX` sessions;
- 324 target rows across three horizons, of which 99 abstained;
- benchmark snapshot SHA-256
  `9596e24cb8837c6943966b6ef0b3cb6c927b3c12c5d1a236c0ef0255730e237d`;
- market snapshot SHA-256
  `4c6cafbed6d20c1b818dad994b544efa36cd1b8bfd8be0b837c909f644156bf7`;
- reaction snapshot SHA-256
  `96f125e0c17b4255bb0e183ff88851a4698775f6fd377c8eccbfac76cf2d0805`.

## Sealed-test boundary

All 108 events are dated in the configured test period. Train and validation are empty. The public
result therefore does not inspect or disclose test return distributions or reaction-class counts.
The fixed thresholds are exploratory configuration values only and were not selected from test.

This establishes implementation feasibility and lineage, but not a training-ready dataset,
prediction quality, sentiment validity or causal event impact. Downstream selection and training
remain blocked until an audited historical official-event source provides non-empty chronological
train and validation coverage. FinMind news remains conditional metadata and is not silently
promoted to a reaction-event source.

The follow-up metadata audit found no documented historical date-range API for the official daily
TWSE OpenAPI feed. The MOPS interactive history page is not treated as a bulk API and must not be
reverse engineered around its security controls. A bounded FinMind audit also failed schema and
timestamp gates, so it remains ineligible as a reaction-event source. See
`m8_historical_event_source_audit.md`.

## Verification

Unit tests cover cutoff/session alignment, horizon computation, missing-price abstention, benchmark
normalization and the invariant that mutating future prices changes only target-side values. The
builder verifies the benchmark checksum and refuses to overwrite differing immutable target files.
All raw prices, benchmark rows, generated labels and the machine report remain in Git-ignored local
storage.
