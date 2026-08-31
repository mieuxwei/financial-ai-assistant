# R0 Project Rebaseline Protocol — Archive

> Historical milestone-control document retained for research provenance; current status is in
> the public README and final release audit.

Status: **FROZEN — R0 complete; next executable unit is B1 only**  
Date: 2026-08-29

## 1. Authoritative project state

### Track A — complete and frozen

Track A is **Stock-Normalized Volatility Surprise Forecasting**. The final research model is Ridge
Regression with `alpha=100`. F1–F7, the continuous target, temporal folds, 23-feature contract,
historical OOS evidence, model artifact and hashes are immutable.

Track A must not be reopened. Do not rerun M7, change the target/folds, retune Ridge, add price
models, create regime-specific models, manufacture a pristine historical holdout or claim
prospective validation.

### Track B — active

Track B is **Taiwan Financial Sentiment / Impact Modeling and Financial NLP Intelligence**.
Chinese/Taiwan sentiment currently remains `ABSTAIN / CHINESE_SENTIMENT_NOT_VALIDATED`. The active
path uses auditable financial text, allowed/licensed/public research data, open-source models and
project-owned reproducible processing. Zero manual annotation, manual label review and human
adjudication remain hard constraints.

### Track C — product

- F10 FastAPI backend: **COMPLETE**, local research contract, not deployed.
- F11A controlled Streamlit dashboard: **COMPLETE**, not deployed.
- F11B LINE/GAS integration: **PENDING**.
- F12 portfolio finalization: **PENDING AND LAST**.

## 2. One canonical execution sequence

```text
R0 Project Rebaseline & GAS Safety Freeze
  → B1 Source Candidate Audit
  → B2 Taiwan Financial Text Dataset
  → B3 Domain Adaptation & Candidate Signals
  → B4 Validation / Abstention Decision
  → B5 NLP Intelligence Integration
  → F11B-0 GAS Immutable Backup & Migration Copy
  → F11B-1 Controlled LINE Financial AI Integration
  → F11B-2 Current-Market Feature / Risk Integration (only if separately validated)
  → B6 / F9 Optional NLP Incremental-Value Study
  → F12 Portfolio Finalization
```

R0 created the F11B-0 backup artifacts early as an allowed safety prerequisite. That does not
authorize F11B-1, change the canonical order or make the live GAS project modifiable during R0.

Track A is absent from the active queue because it is complete/frozen. Do not interleave B1–B4 or
start F12 early. After R0, the next one executable unit is **B1 only**.

## 3. Track B stages and Definition of Done

### B1 — Source Candidate Audit

Purpose: choose actual Taiwan financial-text sources without training or data collection beyond
separately authorized bounded audits.

Candidate classes may include TWSE, TPEx, official MOPS feeds, GDELT, suitable Taiwan financial
news, the approved FSC corpus, licensed academic sources and optional AP11.

Definition of Done:

- each candidate has a purpose-specific `ACCEPT`, `CONDITIONAL`, `HOLD` or `REJECT` decision;
- provenance, access, language, ticker mapping, content fields, timestamp/timezone semantics,
  coverage, duplicates, revisions, delays, missingness, storage and redistribution rights are
  documented;
- accepted purposes and prohibited uses are explicit;
- no training, pseudo-labeling, manual labels or active eLAND work occurs;
- a frozen source manifest identifies exactly what may enter B2.

### B2 — Taiwan Financial Text Dataset

Only B1-approved sources may enter.

Definition of Done:

- one versioned normalized schema covers `source_id`, `document_id`, `source_type`, ticker/company,
  publication timestamp/timezone, language, permitted title/text/excerpt/reference,
  event category, provenance, licensing metadata and ingestion version;
- deterministic ticker mapping, timestamp normalization, deduplication and source lineage pass;
- training/evaluation availability and retention rules are frozen;
- duplicate, coverage, missingness and rights reports are raw-free and reproducible;
- no sentiment model training occurs before the dataset/version is accepted and frozen.

### B3 — Domain Adaptation & Candidate Signals

Compact candidate set:

- deterministic/lexicon baseline;
- one justified open-source Chinese financial baseline;
- one justified open-source multilingual financial baseline;
- BERT-base-Chinese;
- MacBERT or one justified Chinese encoder;
- project-owned financial-domain-adapted Chinese encoder.

Definition of Done:

- all candidates have pinned revisions, licenses, input versions and reproducible configs;
- only B2-approved train partitions/corpora are used;
- the existing FSC/BERT/MacBERT evidence is reused where compatible and not falsely relabeled;
- no large model zoo, eLAND, future leakage or manual labels are introduced;
- candidate outputs distinguish sentiment, event, impact and market-reaction concepts.

### B4 — Validation / Abstention Decision

Frozen preferred sentiment gate:

```text
Macro-F1 >= 0.70
AND recall >= 0.60 for every required class
```

Definition of Done:

- thresholds are frozen before evaluation and are not lowered after seeing results;
- chronological/family/source isolation and leakage tests pass;
- results report class metrics, coverage, abstention, uncertainty and failure modes;
- maturity is declared `VALIDATED`, `AUTOMATED_SIGNAL_ONLY` or `ABSTAIN`;
- no automated or market-reaction proxy is called human-validated sentiment truth.

### B5 — NLP Intelligence Integration

Definition of Done:

- F8/F10 intelligence contracts accept only B4-supported capabilities;
- unsupported Chinese polarity remains explicit abstention with null probabilities;
- event classification, ticker matching, source-aware intelligence, embeddings, retrieval,
  keyphrases, structured summaries, impact signals and media-tone proxies remain separately typed;
- lineage, licensing, service errors and claim boundaries are exposed and tested;
- no provider/model work runs implicitly during a public request unless separately designed and
  authorized.

### B6 / F9 — optional incremental-value study

Definition of Done, only if run:

- a sufficiently clean timestamp-safe historical NLP feature dataset already exists;
- Market-only versus Market+NLP uses the same frozen Track A target, folds and model discipline;
- paired ablation, coverage and null/negative results are reported honestly;
- no positive NLP lift is required for project completion.

## 4. Source decisions frozen at R0

- AP11: **OPTIONAL enhancement**; not required before B1, Chinese NLP, F11B or F12.
- eLAND: **PERMANENT HISTORICAL EXCLUSION**; no datasets, models, API calls, audits, weak votes,
  features, training or revival.
- TWMD: **HOLD / currently unavailable** after three HTTP 402 entitlement probes; do not call paid
  datasets during R0/B1 unless separately authorized later.
- FinMind `TaiwanStockNews`: conditional for deduplicated title-level intelligence; HOLD for direct
  reaction weak supervision and rich-text training.
- Official filtered FSC corpus: accepted only for the documented non-commercial unlabeled
  domain-adaptation purpose; never sentiment truth.

## 5. F11B stages and Definition of Done

### F11B-0 — immutable backup and migration copy

Definition of Done:

- original `code.gs` and `appsscript.json` are copied byte-for-byte into private ignored storage;
- original/copy hashes and `cmp` verification match;
- immutable backup is read-only and migration copy is separate;
- property names, functions, scopes and accessible deployment/trigger facts are inventoried without
  recording secret values or private identifiers;
- the sole working original is not modified.

R0 satisfied this safety prerequisite. See `docs/gas_migration_safety_freeze.md`.

### F11B-1 — controlled LINE Financial AI integration

Definition of Done:

- only additive `risk <ticker>`, `intel <ticker>` and optional `news <ticker>` routing is added to
  the migration copy/existing bot architecture;
- legacy commands, holdings, Sheet schema, screenshots and schedules remain unchanged;
- initial responses use a deterministic fixture or stored validated snapshot and say
  `CONTROLLED RESEARCH DEMO`;
- GAS-to-FastAPI authentication, replay protection, timeout/error behavior, identity mapping,
  rate limiting and audit requirements are implemented/tested before any live connection;
- rollback to the immutable source is demonstrated; no deployment occurs without its own gate.

### F11B-2 — current-market feature/risk integration

Definition of Done:

- an audited current OHLCV and TAIEX source exists;
- the exact 23 F7 features have session-cutoff, timezone, missing-data and lineage rules;
- parity tests prove current feature calculation matches the frozen historical contract;
- GAS does not implement an ad-hoc 23-feature substitute;
- current inference is separately validated before the controlled-demo label is removed.

### F12 — portfolio finalization

Definition of Done:

- frozen Track A, B1–B5 status, F10, F11A and completed/limited F11B are represented honestly;
- final README/workflow, model comparison, ranking/robustness visualizations, abstract, demo script,
  security/privacy limits and non-investment disclaimers are complete;
- unfinished B6/F9, prospective validation, live deployment and portfolio-write migration are
  clearly future/optional work;
- tests, lint, secret scan and reproducibility checks pass with no private data committed.

## 6. R0 stop boundary

R0 changes documentation and creates private ignored GAS safety copies only. It does not collect
B1 data, train models, create labels, modify live GAS behavior, deploy, alter triggers/webhooks,
touch holdings/Sheets, rerun Track A, commit or push.

Stop after R0. Continue with **B1 Source Candidate Audit** only after explicit user instruction.
