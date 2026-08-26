# M6 Feature Definitions

Status: **preserved legacy direction-prediction foundation**. The cutoff alignment, market-feature
formulas, snapshot hashing and leakage tests may be reused by new Track A. `forward_return_1d` and
`label_up` do not define the new volatility-risk target. New M2 will introduce a separate versioned,
train-only `NORMAL` / `HIGH_RISK` label protocol without overwriting this document or `features-v1`.

## Row and time contract

Each row uses an observed trading session `t` and predicts the next observed session. The initial Taiwan-market contract uses Asia/Taipei 13:30 as the information cutoff. OHLCV for `t` is assumed available only after this cutoff, so this dataset is for post-close research and next-session prediction, not intraday trading.

At least 26 price observations are required before a row, and one later observation is required for its label. Inputs should include sufficient warm-up history before the desired evaluation period.

## Market features

All close-based calculations use adjusted close and end at `t`:

- `return_1d`, `return_3d`, `return_5d`, `return_20d`: trailing adjusted-close percentage changes.
- `ma_5_deviation`, `ma_20_deviation`: current adjusted close divided by the trailing moving average, minus one.
- `volume_change_1d`: one-session volume percentage change; null if the prior volume is zero.
- `volume_zscore_20d`: current volume z-score over the trailing 20 sessions; zero for a constant window.
- `volatility_5d`, `volatility_20d`: population standard deviation of trailing daily returns, not annualized.
- `rsi_14d`: simple-average RSI; 100 with gains and no losses, 50 when all changes are zero.
- `macd_12_26`, `macd_signal_9`: recursive EMA MACD and its signal line, seeded from the first input close.
- `benchmark_return_1d`: same-date one-session return of the configured benchmark; null when unavailable.

## Sentiment features

Publications at or before the cutoff enter the same trading session. Later publications and non-trading-day publications enter the next observed session for that ticker.

For 1, 3 and 5 observed-session windows, the dataset includes:

- article count;
- mean positive, neutral and negative probability;
- mean and population standard deviation of `positive_prob - negative_prob`;
- relevance-weighted sentiment score;
- positive and negative argmax-label ratios.

Every window also records separate count and mean-score fields for official announcements and general news (`source_type != official_announcement`). When no supported sentiment result exists, count fields are zero while probability, score and ratio fields are null. This distinguishes “no supported information” from genuine neutral sentiment.

## Label and reproducibility

`forward_return_1d = adjusted_close(target) / adjusted_close(t) - 1`. `label_up` is 1 only for a strictly positive value. The ordered dataset, normalized upstream observations and complete configuration receive independent SHA-256 hashes. Run UUIDs and operational timestamps are excluded.

M6 does not impute, scale or select features. Those transformations belong inside M7 train-only model pipelines.
