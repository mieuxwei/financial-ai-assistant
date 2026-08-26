# Taiwan Financial Annotation Protocol v1.1

Status: retained AI-to-AI diagnostic protocol; not a human-annotation workflow

Schema: `taiwan-financial-annotation-v1`

Taxonomy: `taiwan-event-taxonomy-v1`

Impact labels: `taiwan-impact-labels-v1`

This document preserves the taxonomy and the historical AI-to-AI diagnostic instructions. The
project no longer operates a human annotation or review workflow. The authoritative forward-looking
contract is `docs/automated_chinese_text_signal_protocol.md`.

## 1. Purpose and task boundary

The task is entity-specific Taiwan financial event and impact annotation. It is not stock-price prediction, investment advice, generic emotional tone or a retrospective explanation of market movement.

For the retained historical AI-to-AI diagnostic, automated labelers answered two independent
questions using only the retained title/context available at publication time:

1. What event type is described?
2. Does the available text indicate a positive, neutral, negative or ambiguous financial impact for the specified company?

Automated labelers must not inspect later stock returns, analyst reactions or subsequent
disclosures. Historical market reaction is built separately under the M8 protocol.

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

### 3.1 Prospective boundary rules from calibration round 1

These rules clarify use of the existing code set; they apply prospectively and do not overwrite the
round-1 labels.

- Use the most specific applicable event code. `OTHER` is a last resort, not a synonym for routine.
- Asset acquisitions/disposals, securities or fund investments, leases, guarantees and loans are
  `MATERIAL_TRANSACTION` even when they are routine. Routine affects impact, not event type.
- A director, supervisor, executive, spokesperson or governance-role appointment/replacement is
  `MANAGEMENT_CHANGE` even when described as an administrative change.
- A meeting or investor-conference notice is `OTHER` unless the retained text itself contains a
  formal forward-looking statement; merely promising to discuss outlook is not `GUIDANCE`.
- A media forecast that the company explicitly disclaims is not company `GUIDANCE`; classify the
  underlying disclosure, normally `OTHER`, and assess impact from the clarification itself.
- Treasury-share purchase/execution/cancellation is `BUYBACK`. Use `CAPITAL_REDUCTION` for other
  reductions of paid-in capital, including cancellation of restricted employee shares, unless the
  primary event is explicitly a treasury-share action.
- Classify a target company's own issuance or capital raising as `CAPITAL_INCREASE`. A parent or
  subsidiary merely acquiring shares in another entity is normally `MATERIAL_TRANSACTION`.
- A correction with no new economic event is `OTHER`; if the correction changes a material
  financial result, use the event type of the corrected result.

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

### 4.1 NEUTRAL versus AMBIGUOUS decision rule

- Use `NEUTRAL` when the event is understood and the retained disclosure is routine, procedural or
  directionless, even if an investor could imagine generic risks or benefits.
- Use `AMBIGUOUS` only when a necessary fact is missing, the text contains competing effects, or two
  plausible directions are supported by record-specific evidence. State that missing fact or
  conflict in `ambiguous_reason`.
- Do not create ambiguity solely from generic statements such as “an investment can gain or lose”
  or “a guarantee creates risk”. Conversely, do not force a material transaction to `NEUTRAL` when
  the disclosed terms themselves create a concrete unresolved trade-off.
- For timing-only changes, label the change being announced rather than re-labelling the unchanged
  underlying event. For example, moving an already-decided dividend payment date is normally
  `DIVIDEND` + `NEUTRAL`.
- When several financial horizons conflict in one disclosure and no primary measure is defined, use
  `AMBIGUOUS`. If the title and filing define a primary period, use that period and document the
  comparison basis.

## 5. Confidence and abstention

- `3`: explicit evidence and direct rule match.
- `2`: reasonable interpretation with limited uncertainty.
- `1`: weak evidence; normally use `AMBIGUOUS` or exclude.

Automated labelers are encouraged to abstain. Low confidence must never be converted automatically
to neutral.

## 6. Automated diagnostic workflow and quality control

1. Run independent automated labelers using versioned model identifiers and prompt hashes.
2. Calculate agreement separately for event type and impact; also report raw agreement, label
   distributions and disagreement pairs.
3. Preserve disagreements. A versioned consensus rule may map them to `AMBIGUOUS` or `ABSTAIN`, but
   no human adjudication is performed.
4. Never silently rewrite historical AI outputs after prompt or taxonomy changes; create a new run.
5. Automated labels remain silver signals and must not set a semantic gold-truth flag.

Model-to-model agreement is useful for stability and guideline diagnostics, but it is not semantic
accuracy or human inter-annotator agreement. The operative research contract is
`docs/automated_chinese_text_signal_protocol.md`.

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

## 10. Automated-signal criteria for M9/M11

Proceed to automated signal experiments only when:

- signal schema, taxonomy, prompt and consensus versions are fixed;
- source data pass provenance, licence, duplicate and split-leakage review;
- every output records its automated provenance and normalized-input hash;
- invalid or conflicting outputs remain missing, `AMBIGUOUS` or `ABSTAIN`;
- adoption is evaluated on chronological out-of-sample market-prediction tasks;
- no raw external dataset is tracked by Git.

There is no human gold-set or human-review gate. AI-to-AI agreement is reported as a stability
diagnostic only. Downstream experiments must not claim Chinese semantic accuracy; they may claim only measured
incremental predictive value, coverage, abstention and stability under the automated-signal
protocol.
