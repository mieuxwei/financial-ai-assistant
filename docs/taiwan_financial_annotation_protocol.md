# Taiwan Financial Annotation Protocol v1

Status: draft for M6.1 review  
Schema: `taiwan-financial-annotation-v1`  
Taxonomy: `taiwan-event-taxonomy-v1`  
Impact labels: `taiwan-impact-labels-v1`

## 1. Purpose and task boundary

The task is entity-specific Taiwan financial event and impact annotation. It is not stock-price prediction, investment advice, generic emotional tone or a retrospective explanation of market movement.

Annotators answer two independent questions using only the retained title/context available at publication time:

1. What event type is described?
2. Does the available text indicate a positive, neutral, negative or ambiguous financial impact for the specified company?

Annotators must not inspect later stock returns, analyst reactions or subsequent disclosures. Historical market reaction is built separately in M6.3.

## 2. Inclusion and exclusion

Include a sample only when it has a traceable public source, publication timestamp, target ticker/entity and legally retained title or short context. The text must describe a company-specific event covered by taxonomy v1.

Exclude or flag when:

- the target company cannot be identified;
- the text is corrupted, truncated beyond interpretation or mostly markup;
- it is unrelated commentary, astrology, entertainment, generic politics or product chatter;
- only a later price move makes the intended label apparent;
- the source or retention right is unknown;
- it duplicates another retained event group;
- it contains unnecessary personal or private information.

Excluded records retain metadata, reason and hash for audit but are not training data.

## 3. Event taxonomy

The canonical codes and definitions are stored in `research/configs/taiwan_event_taxonomy.v1.json`.

- `EARNINGS`: profit, loss, financial statements or material financial results.
- `REVENUE`: monthly/quarterly revenue and revenue growth or decline.
- `DIVIDEND`: dividend and earnings-distribution decisions.
- `BUYBACK`: treasury-share purchase, execution or cancellation.
- `CAPITAL_INCREASE`: new shares, private placement or capital raising.
- `CAPITAL_REDUCTION`: capital reduction, loss coverage or capital repayment.
- `M&A`: merger, acquisition, share swap, split or control transaction.
- `REGULATORY`: approval, penalty, investigation, compliance or material litigation.
- `MANAGEMENT_CHANGE`: board, executive, spokesperson or governance-role change.
- `GUIDANCE`: formal forward-looking operating or financial outlook.
- `MATERIAL_TRANSACTION`: material contract, asset transaction, guarantee or loan.
- `OTHER`: an included material company event outside the listed types.

If one disclosure contains multiple events, annotate the primary event for v1 and record the ambiguity. Multi-label taxonomy is deferred and requires a new taxonomy version.

## 4. Impact labels

### POSITIVE

The retained text itself supports a clearly favourable direction for the specified company. Synthetic examples include a material contract explicitly increasing secured orders or audited results showing a clear improvement without an offsetting issue.

### NEGATIVE

The text itself supports a clearly adverse direction, such as a material penalty, production suspension, contract termination or audited deterioration without a stated offset.

### NEUTRAL

Routine or administrative disclosure with no explicit favourable/adverse direction, such as announcing a meeting date or a procedural filing. Neutral means the event is interpretable and directionless; it does not mean “model uncertain”.

### AMBIGUOUS

Use when information is insufficient, effects conflict, terms depend on missing context, or trained reviewers can reasonably disagree. Examples include capital raising without use-of-proceeds context or a management change without cause/effect information. An `ambiguous_reason` is mandatory.

Do not infer that every dividend or buyback is positive, every capital increase is negative, or every management change is adverse. The retained context controls the label.

## 5. Confidence and abstention

- `3`: explicit evidence and direct rule match.
- `2`: reasonable interpretation with limited uncertainty.
- `1`: weak evidence; normally use `AMBIGUOUS` or exclude.

Annotators are encouraged to abstain. Low confidence must never be converted automatically to neutral.

## 6. Annotation workflow and quality control

1. Run a 30-item calibration round using synthetic/public examples not in the sealed test.
2. Review disagreements and revise only the guideline version, never silently rewrite history.
3. Double-annotate the entire sealed test and at least 20% of train/validation.
4. Calculate Cohen's kappa separately for event type and impact; also report raw agreement and per-class disagreement.
5. If kappa is below 0.60, pause scale-up, revise rules and run a new calibration set.
6. Mark disagreements `CONFLICT`; an independent reviewer adjudicates without seeing future returns.
7. Only `REVIEWED` or `ADJUDICATED` records can set `include_for_training=true`.

The project owner does not need to be the financial expert. A trained reviewer can label obvious cases; ambiguous/domain-specific conflicts should be escalated to a finance instructor, finance student or another documented reviewer. External labels remain silver until this QC contract is satisfied.

## 7. Leakage-safe split

- Normalize and hash retained text before splitting.
- Group the same source record, follow-up/correction, exact duplicate and near-duplicate rewrite under one `split_group_id`.
- Sort groups chronologically. Train is earliest, validation follows, and final test is latest and sealed.
- Do not rebalance by moving duplicates across time boundaries.
- The current 30-item TWSE diagnostic stays frozen and outside training/threshold selection.
- Preprocessing, class weights, threshold and calibration fit on train/validation only.

## 8. Source, copyright and privacy

- Save source name, type, original URL, record ID and publication timestamp.
- Retain only title and legally necessary short context; do not copy full paid/licensed articles.
- A dataset-level licence does not by itself prove redistribution rights for underlying source text.
- Do not commit downloaded third-party raw data. Keep it under ignored `.tools/` or `data/raw/`.
- Remove unnecessary personal names and private data. Public role names are retained only when essential to the event.
- Publish aggregate audit statistics and hashes, not unreviewed external text.

## 9. Versioning and change control

Every record carries schema, taxonomy and label versions. Definition changes require a new version, migration note and re-evaluation. Existing labels are never overwritten without an auditable adjudication record.

## 10. Go/no-go criteria for M6.2

Proceed to encoder training only when:

- schema/taxonomy/guideline are approved;
- candidate data pass provenance, licence, duplicate and split-leakage review;
- a sealed, independently reviewed Taiwan-domain test exists;
- all classes have enough reviewed examples for per-class recall evaluation;
- annotation agreement meets the approved threshold;
- no raw external dataset is tracked by Git.

