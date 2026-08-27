# M3 Market-Only Risk Feature Protocol

Pipeline version: `risk-features-v1`  
Configuration: `research/configs/risk_features.v1.json`

## Boundary

M3 joins the immutable M1 market snapshot to the M2 train/validation risk-label rows. Every feature
uses information available at the post-close session `t` cutoff. Target-side `t+1` values are kept
under a separate `target` object and never enter the `features` mapping.

M3 performs no imputation, scaling, feature selection, class weighting, resampling, model fitting,
or NLP enrichment. Sealed-test features are not materialized.

## Availability rule

A feature row requires 35 consecutive TAIEX benchmark sessions ending at `t`, with a valid stock
bar on every session. The fixed 35-session window covers the longest v1 technical calculation
(26-session slow EMA plus 9-session signal context). If any required stock bar is missing, the row
abstains; it is not forward-filled and the window is not bridged across the gap.

The builder verifies the M2 SHA-256 commitment to the final 21-session `t` state before computing
features. The M1 dataset hash, M2 label-dataset hash, config hash, feature-row hash, target-row hash,
and complete M3 dataset hash preserve lineage.

## Feature groups

All log returns use adjusted close unless stated otherwise. Population standard deviation uses
`ddof=0`.

### Price — 7

- `return_log_1`, `return_log_5`, `return_log_10`, `return_log_20`:
  `ln(adjusted_close_t / adjusted_close_{t-k})`.
- `overnight_gap_log_1`: `ln(open_t / raw_close_{t-1})`.
- `close_ma_deviation_5`, `close_ma_deviation_20`:
  `adjusted_close_t / trailing_mean(adjusted_close, k) - 1`.

### Volume — 3

- `volume_log_change_1p_1`: `ln(1 + volume_t) - ln(1 + volume_{t-1})`.
- `volume_zscore_20`: population z-score of current volume in the trailing 20 sessions; zero when
  the window is constant.
- `zero_volume_flag`: one only when current reported volume is zero.

### Volatility and range — 5

- `volatility_log_return_5`, `volatility_log_return_20`: population standard deviation of trailing
  one-session log returns.
- `high_low_log_range_1`: `ln(high_t / low_t)`.
- `atr_14_normalized`: mean 14-session true range divided by current raw close.
- `parkinson_mean_5`: mean of `abs(ln(high/low)) / sqrt(4 ln 2)` over five sessions.

### Compact technical — 3

- `rsi_14`: simple-average 14-session RSI, with 50 for no movement and 100 for gains with no loss.
- `macd_12_26_normalized`: 12/26 EMA difference divided by adjusted close.
- `macd_signal_9_normalized`: 9-span EMA of MACD divided by adjusted close.

EMA recursion is seeded at the oldest observation in the fixed 35-session window. This makes the
calculation finite, reproducible, and independent of data before the declared window.

### TAIEX market context — 5

- `benchmark_return_log_1`, `benchmark_return_log_20`: TAIEX total-return-index log returns.
- `benchmark_volatility_log_return_20`: trailing 20-session TAIEX log-return volatility.
- `stock_minus_benchmark_return_log_1`: stock one-session return minus TAIEX return.
- `benchmark_drawdown_20`: current TAIEX value divided by its trailing 20-session maximum, minus one.

The universe contains listed securities only, so TAIEX is an appropriate broad-market context for
this bounded study. It is not claimed to explain every stock-specific movement.

## Leakage and sealing tests

Automated tests establish that:

- mutating stock `t+1` changes target outcome but not the `t` feature dictionary or feature hash;
- mutating TAIEX at `t+1` does not change the same-day market-context features;
- formula-level stock return, benchmark return, and stock-minus-market values match independent
  calculations;
- M1/M2 hashes, target-session adjacency, split containment, cutoff timezone, and M2 feature-state
  commitments are verified;
- test split configuration is rejected and sealed-test features remain absent;
- every output row has exactly 23 finite, non-null features;
- immutable output cannot silently overwrite different content.

The `target` object is retained for later train/validation modeling but is structurally separate
from the feature mapping. `HIGH_RISK` remains a research label, not direction or investment advice.
