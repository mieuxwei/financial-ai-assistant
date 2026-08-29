# B2.1 TWMD Secondary-Source Result

Run date: 2026-08-29  
Decision: **PASS — secondary-source contract and fail-closed provider ready**  
Dataset ingestion: **none**  
B3: **not started**

## Delivered

- frozen contract: `research/configs/b2_1_twmd_secondary_source.v1.json`;
- source decision: `research/configs/twmd_pro_source_decision.v1.json`;
- provider and normalized licensed-metadata schema:
  `pipelines/news/twmd_major_events.py`;
- request helper extended with optional parameters/headers without changing existing callers:
  `pipelines/news/http.py`;
- contract documentation: `docs/b2_1_twmd_secondary_source_contract.md`;
- unit tests: `tests/unit/test_twmd_major_events.py`.

Frozen SHA-256 values:

- contract config: `89491f4cefe1d417bef47c53d4dc1d1e216e3f7dcdcfb5ebd0da8f0bd2e65edb`;
- provider/schema: `6a286d837da98f8de32b5f44db7e0a699a558e5d870f63eb0d956fba4f8a6b27`;
- source decision: `752ae370bd186ec827591a1ed7e60f9fc406da640122e73e24bf694ce0c000c5`.

## Frozen safeguards

The implementation:

- uses only live runtime fields `ticker/date_from/date_to/limit`;
- requires the response to echo every filter;
- rejects different tickers and out-of-window dates;
- limits a request to one ticker, 31 days, 100 rows and 1 MB;
- rejects a page reaching the requested limit instead of accepting possible truncation;
- parses `event_date + event_time` as Asia/Taipei under an explicit no-offset assumption;
- requires ticker, market, date, time, subject, class, confidence and rule version;
- assigns stable document/version hashes and counts exact duplicates;
- marks records `LICENSED_EVENT_METADATA_PRIVATE`;
- fixes `full_text_available=false`, `sentiment_ground_truth=false` and
  `human_validated=false`;
- never records the API key.

## Completion boundary

B2.1 passes as a source-contract amendment. No live request, historical backfill, dataset snapshot,
training, evaluation, GAS change, Track A change, deployment, commit or push occurred during this
unit. The four tiny 2018/2024 rows remain only evidence from the preceding entitlement re-audit and
were not promoted into B2.

B2 v1 therefore remains the only active B3 dataset. The next executable unit can be B3 using B2
v1, subject to explicit user approval. If TWMD rows are desired in B3, a bounded private dataset
construction and coverage report must be approved first.
