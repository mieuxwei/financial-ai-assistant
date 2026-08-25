# Experiment Protocol

Experiments will compare a price/volume/technical baseline with an otherwise matched model that also includes news-sentiment features. Time-aware splits and leakage controls are required.

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

M3 market snapshots are ordered by ticker and trading date and include a deterministic SHA-256. Research configurations must record the snapshot checksum, provider, requested range, and canonical universe. `ingested_at` is intentionally excluded from the checksum because it is operational metadata rather than market information.

Yahoo raw OHLC values are normalized to six decimal places and its derived adjusted close to three decimal places. Existing adjusted-close changes of `0.005` or less retain the stored value; larger changes create a new dataset revision. This rule is part of snapshot schema `market-prices-v1`.

Potential weekday gaps must not automatically be forward-filled. They require exchange-calendar verification before feature or label generation.
