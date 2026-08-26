# M9 Weak-Supervision Core Result

Date: 2026-08-26  
Status: minimal aggregation core complete; real-source execution pending

## Implemented

- Versioned `WeakVote` contract for official-category mappings, deterministic rules, local models,
  translation plus FinBERT and optional structured LLM sources.
- Mandatory labeling-function ID/revision and normalized-input SHA-256.
- Mandatory model version for model-backed votes and prompt SHA-256 for LLM votes.
- Reproducible confidence-weighted voting with configurable source weights and minimum margin.
- Separate `official_source_category` and automatically inferred `normalized_event_type` fields.
- Output coverage, agreement, normalized vote entropy, source/model/prompt provenance, abstention
  reasons and immutable vote snapshot SHA-256.
- Conservative deterministic event/impact cues. No match abstains; opposing impact cues produce
  `AMBIGUOUS`; absence of a cue never becomes neutral.

At least two independently identified sources are required. Insufficient sources produce
`INSUFFICIENT_INDEPENDENT_SOURCES`; unresolved vote margins produce `AMBIGUOUS` for impact or an
event-type abstention. There is no manual adjudication path.

## Claims and data boundary

The tests use synthetic strings only. No TWSE sealed-test event, market-reaction target, paid LLM,
translation service or external model was read or called. These outputs are silver research
signals, not human labels, expert judgment, linguistic sentiment truth or investment advice.

The core is not a completed M9 experiment. Before a real run, each labeling function needs a pinned
implementation/revision, approved input source, chronological split policy and raw-free report.
Local frozen-model and translation/FinBERT adapters remain pending; optional LLM remains disabled by
default. Adoption still depends on downstream chronological out-of-sample incremental value.
