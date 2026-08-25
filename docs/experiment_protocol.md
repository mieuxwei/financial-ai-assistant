# Experiment Protocol

Experiments will compare a price/volume/technical baseline with otherwise matched models that add news count, English sentiment, Taiwan event/impact and historical market-reaction signals. These concepts remain separate, and all comparisons require time-aware splits and leakage controls.

## M5 sentiment reproducibility contract

- Model: `ProsusAI/finbert` at revision `4556d13015211d73dccd3fdd39d39232506f3e43`.
- Runtime inference uses evaluation mode, inference mode, a fixed PyTorch seed and deterministic algorithms.
- Each stored output includes a model version and SHA-256 of the exact normalized input text plus model version.
- Probabilities are stored to eight decimal places; the continuous score is `positive_prob - negative_prob`.
- English is supported. Chinese input is excluded rather than translated or assigned neutral.
- Calendar-day sentiment uses Asia/Taipei dates. Trading-session cutoffs are deferred to M6.
- The manual sample is a small synthetic regression/error-analysis set, not a performance benchmark.

## M5.1 Chinese adoption gate

Chinese model selection uses both a balanced synthetic regression set and a separate TWSE announcement-derived context set. A candidate must reach macro-F1 ≥ 0.70 and recall ≥ 0.60 for positive, neutral and negative on the TWSE set. Timing is diagnostic only and excluded from reproducibility hashes.

No tested M5.1 candidate passed. Chinese results remain missing-by-design rather than neutral. Future model training must use a separate train split; the current TWSE sample becomes evaluation-only and must not be used to tune lexicons, thresholds or model weights.

The explicit rejection evidence is retained: lexicon macro-F1 0.320, yiyang 0.357, bards.ai 0.442, translation plus English FinBERT 0.592, and Kenpache multilingual-v2 0.640. The gate remains macro-F1 ≥ 0.70 and recall ≥ 0.60 for every required class.

## M6.1 Taiwan annotation protocol contract

- The target concepts are a versioned event type and entity-specific financial impact: positive, neutral, negative or ambiguous.
- Linguistic tone, financial impact and observed future price reaction must not be treated as interchangeable labels.
- Inclusion, exclusion, abstention, reviewer, adjudication, agreement and copyright/source rules must be approved before annotation scale-up.
- Near-duplicate disclosures and their rewrites belong to the same split. Train is earlier, validation is used for selection, and final test remains sealed.
- The 30-item TWSE-derived set stays a frozen diagnostic artifact and is not sufficient for training or a publishable benchmark.
- Candidate public data must pass provenance, licence, label, duplicate and split-leakage audits before use.

## M6.2 Taiwan model adoption contract

- MacBERT is a candidate encoder, not a preselected winner.
- Fine-tuning uses training data only; model, threshold and calibration choices use validation only.
- A candidate must meet the approved gate on a sealed Taiwan-domain test before formal inference is enabled.
- Failed candidates and negative findings remain in the report. Unsupported text never receives fabricated probabilities or a neutral placeholder.

## M6.3 historical market-reaction contract

- Candidate targets include next-session, 1-day and 3-day returns, preferably adjusted by a benchmark or market return.
- The publication timestamp and market cutoff determine the reaction window; same-session article collections are treated as one information set when causal attribution is not identifiable.
- Future return is allowed only as an offline target/label. It is forbidden as an input available at the event time.
- Any reaction-derived input at prediction time must use only events whose reaction windows finished before that prediction cutoff.
- Target thresholds, beta estimates and normalisation are fit on train only and then frozen.

## M7 downstream comparison contract

The comparison matrix includes majority/previous-direction, market-only, market plus news count, market plus English FinBERT, market plus Taiwan event/impact, market plus historical reaction, and the combined model. Signal-group ablations remove each group independently. Model selection uses chronological validation, the final test stays sealed, and walk-forward analysis checks regime stability.

## M6 feature and label contract

- One row represents information available at the Asia/Taipei 13:30 close of trading session `t`.
- The target is the next observed session, not `t + 1` calendar day. `label_up = 1` only when adjusted-close return is strictly positive; zero return belongs to class 0.
- Every return, moving average, volume statistic, volatility, RSI and MACD value ends at `t`. A leakage test mutates `t+1` and requires `t` features to remain byte-equivalent while its label changes.
- News at or before the cutoff enters session `t`; news after the cutoff or on a non-trading day enters the next observed session.
- Sentiment rolling windows use 1, 3 and 5 observed trading sessions. No-article probability and score fields are null, not zero or neutral; article counts are zero.
- The modeling dataset records exact configuration, pipeline version, market snapshot hash, sentiment snapshot hash and dataset hash. Rebuilding identical database inputs must reproduce the hash.
- M7 preprocessing, imputation, scaling, feature selection and threshold selection must fit on the training period only. M6 intentionally performs none of those steps.

M3 market snapshots are ordered by ticker and trading date and include a deterministic SHA-256. Research configurations must record the snapshot checksum, provider, requested range, and canonical universe. `ingested_at` is intentionally excluded from the checksum because it is operational metadata rather than market information.

Yahoo raw OHLC values are normalized to six decimal places and its derived adjusted close to three decimal places. Existing adjusted-close changes of `0.005` or less retain the stored value; larger changes create a new dataset revision. This rule is part of snapshot schema `market-prices-v1`.

Potential weekday gaps must not automatically be forward-filled. They require exchange-calendar verification before feature or label generation.
