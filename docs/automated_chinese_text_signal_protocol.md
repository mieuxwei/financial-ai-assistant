# Zero-Manual-Label Taiwan Financial Learning Protocol v1

Status: approved research direction

## Scope

The project uses no human annotation or human label review. Chinese financial text outputs are
automated research signals, not human-validated sentiment or expert labels.

The primary research question is whether automated text-derived features improve strictly
out-of-sample short-horizon direction prediction beyond price, volume and technical features.

Active source audits focus on `tw-finance-159M`, MOPS/TWSE, FinMind, optional Taiwan FSC/regulatory
text and historical stock/benchmark prices, each only for its approved purpose. Eland is a
historical `HOLD` rejection record and is excluded from training, domain adaptation, weak
supervision, evaluation, features and corpus merging.

The learning protocol has three independent automated supervision sources:

1. domain-adaptive language modeling on accepted, audited, unlabelled Taiwan financial corpora;
2. automatic market-reaction labels generated from timestamp-aligned historical prices;
3. aggregation of deterministic rules, official metadata and versioned model weak supervision.

## Signal groups

1. Deterministic metadata: source, official disclosure category, publication timing, ticker
   matches and news counts. Official categories remain separate from inferred event categories.
2. Frozen text representations: versioned embeddings produced without fitting on future periods.
3. AI-derived event/impact proxies: structured outputs from pinned model and prompt versions.
4. Consensus metadata: model agreement, vote entropy, confidence and abstention indicators.
5. Historical market reaction: returns from older events whose reaction windows completed before
   the current prediction cutoff.

Every group must be independently removable for ablation. AI-derived labels remain `silver` and
must never be exposed as expert truth.

## Automated labelling contract

- Use at least two independently configured labelers when generating consensus features.
- Store provider/model identifier, model revision when available, prompt hash, schema version,
  decoding parameters, timestamp and normalized-input hash.
- Parse only schema-valid outputs. Invalid outputs are missing, not silently repaired into neutral.
- Accept consensus only under a versioned rule. Disagreement becomes `AMBIGUOUS` or `ABSTAIN` and
  is retained as a feature rather than manually adjudicated.
- Never use future prices, later disclosures or analyst reactions in event-time text generation.
- Model-to-model agreement measures stability, not semantic correctness.

## Targets and leakage boundary

Prediction targets are generated mechanically from market data, such as next-session direction,
1-day return, 3-day return and benchmark-adjusted abnormal return. Future returns may appear only
on the target side of the event being predicted.

Reaction-derived input features may use only older events whose entire reaction window ended before
the current information cutoff. All cutoffs and snapshot hashes must be retained.

## Evaluation

The adoption decision is based on chronological validation, sealed out-of-sample test and
walk-forward analysis, not comparison with human sentiment labels.

Required comparisons:

- market-only baseline;
- market plus news counts;
- market plus frozen text representations;
- market plus AI event/impact proxies;
- market plus consensus/abstention metadata;
- market plus eligible historical-reaction features;
- combined model and signal-group ablations.

The full experiment matrix is:

- Baseline 0: majority / previous-direction naive baseline;
- Baseline 1: price, volume and technical features;
- Model 2: Baseline 1 plus news counts and deterministic metadata;
- Model 3: Baseline 1 plus validated English sentiment;
- Model 4: Baseline 1 plus Taiwan frozen text representations;
- Model 5: Baseline 1 plus official/inferred event metadata and weak-supervision signals;
- Model 6: Baseline 1 plus eligible past-completed market-reaction features;
- Model 7: combined eligible signal groups.

Model 7 must be accompanied by one-group-at-a-time ablations and comparisons that remove source,
event, representation, weak-label, confidence/abstention and reaction groups independently.

Report predictive metrics, transaction-cost-aware backtest results, coverage, abstention, stability
across periods, bootstrap confidence intervals and failure cases. A text signal is adopted only when
its incremental benefit is reproducible and does not depend on leakage or a single unstable period.

## Claims boundary

Allowed claims:

- an automated text signal improved or failed to improve a specified out-of-sample experiment;
- two automated labelers agreed at a measured rate;
- a signal achieved a stated coverage or abstention rate.

Forbidden claims:

- the Chinese sentiment label is correct or expert validated;
- model-to-model agreement is human inter-annotator agreement;
- silver labels constitute a gold dataset;
- observed historical returns prove the text caused the price move;
- the resulting prediction is investment advice.
