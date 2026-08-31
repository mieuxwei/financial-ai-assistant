# Forward Data Collection Audit

Date: 2026-08-30
Decision: **AUDIT_COMPLETE_IMPLEMENTATION_NOT_READY**

## Purpose

This audit determines whether the existing repository can safely begin naturally future data
collection after portfolio finalization. It does not deploy a scheduler, retrain a model, create
sentiment labels, unlock F11B-2 or convert already inspected history into prospective evidence.

Two collection purposes must remain separate:

1. **Track B official-event collection** may accumulate future TWSE/TPEx disclosures for later
   longitudinal market-reaction research.
2. **Track A official market-data collection** may preserve future source/parity evidence, but it
   cannot yet serve as exact F7 external validation because official adjusted-price lineage is not
   training-equivalent and exact feature parity remains 5/23.

## Bounded source probe

Each official endpoint was called once through the existing provider with one allowed attempt. No
raw payload or normalized row was retained.

| source | status | rows | unique IDs | duplicate IDs | tickers | publication range | timezone |
|---|---|---:|---:|---:|---:|---|---|
| TWSE daily material information | PASS | 7 | 7 | 0 | 7 | 2026-08-29 00:00:24–14:18:25 | Asia/Taipei |
| TPEx daily material information | PASS | 5 | 5 | 0 | 5 | 2026-08-29 07:00:03 | Asia/Taipei |

The feeds were live and parseable in the current environment. A daily official feed may validly
return zero rows on another day; zero is not automatically a failure when the request and schema
checks succeed.

## Existing strengths

- TWSE and TPEx read-only providers use official endpoints and timezone-aware publication times.
- Stable external IDs are derived from ticker, official timestamp and normalized title.
- B2 contains deterministic document/version IDs and immutable write primitives.
- The database path has exact content-hash uniqueness and source-scoped ingestion-run status.
- Rights, retention, public/private boundaries and the no-automatic-retraining rule are frozen.
- No minimum 30/90/126-session waiting period is required to start collection.

## Blocking implementation gaps

The current `jobs/news.py` is an application-news ingestion command, not the frozen B2 forward
collector. It wires TWSE material information and TWSE RSS, but not TPEx, and it does not connect
provider responses to the immutable B2 RAW/NORMALIZED storage path.

Before any private schedule is enabled, the project still needs:

1. a dedicated B2 TWSE/TPEx forward runner;
2. rights-safe immutable raw persistence before normalization;
3. immutable B2 document-version persistence;
4. a source/run manifest with endpoint, retrieval time, row counts and hashes;
5. current-evening-next-morning reconciliation orchestration;
6. a concurrency lock preventing overlapping runs;
7. retry timing aligned with the frozen 1/2-second TWSE/TPEx contract—the shared helper currently
   uses 0.5/1 second;
8. fail-closed partial-source, schema-drift and rerun-idempotency tests;
9. separately approved private scheduler configuration.

Accordingly, source availability is **not** the blocker. The blocker is incomplete orchestration,
storage lineage and schedule safety.

## Track A boundary

F11B-2A remains authoritative:

- official current coverage: 10/10 frozen instruments, all on TWSE;
- training adjusted price: Yahoo `indicators.adjclose`;
- official adjusted-price equivalence: unresolved;
- exact feature parity: 5/23;
- current-serving gates: 6/9;
- F11B-2: blocked.

Official OHLCV collected now may be retained as future lineage/parity evidence. It must not be
silently transformed into F7 inputs or called exact external validation. A future validation using
a changed source/pipeline requires a separately versioned dataset and approved research protocol.

## Research-integrity boundary

Forward collection creates naturally future observations; it does not automatically validate,
retrain or promote a model. Model refresh requires a new candidate version, frozen chronological
evaluation and explicit approval. TWSE/TPEx event text is not Chinese sentiment ground truth, and
market reaction must not be relabelled as linguistic sentiment.

## Historical implementation decision

At the time of this audit, scheduled collection was not yet implementation-ready:

`AUDIT_COMPLETE_IMPLEMENTATION_NOT_READY`

The subsequent private runner and deployment work resolved these implementation gaps. Current
deployment status is documented in `docs/forward_collection_deployment.md`; this file remains the
pre-implementation source audit.
