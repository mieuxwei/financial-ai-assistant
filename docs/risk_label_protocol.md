# M2 Next-Session Volatility Risk Label Protocol

Protocol version: `next-session-volatility-risk-v1`  
Configuration: `research/configs/next_session_volatility_risk.v1.json`

## Prediction contract

Each row represents a post-close prediction made for ticker `i` after exchange session `t` at
13:30 Asia/Taipei. Its target is the immediately following benchmark exchange session `t+1`, never
the next calendar day and never a later available provider row substituted for missing `t+1` data.

The row records:

- ticker, feature session, information cutoff, exact target session, and chronological split;
- a SHA-256 commitment to the full market state used at `t`;
- the continuous primary and secondary next-session outcomes;
- the train-only threshold value and artifact hash;
- `NORMAL` or `HIGH_RISK`.

`HIGH_RISK` means only that the mechanically calculated next-session outcome meets or exceeds the
frozen candidate threshold. It does not predict direction, causation, a loss, or a need to trade.

## Primary outcome

For adjusted close `C` and one-session log return `r`:

```text
r_t = ln(C_t / C_{t-1})
sigma_t = population_std(r_{t-19}, ..., r_t)
primary_outcome_t = abs(ln(C_{t+1} / C_t)) / sigma_t
```

The 20 returns used by `sigma_t` must come from 21 consecutive benchmark sessions with valid stock
bars. `sigma_t` is fully known at the post-close `t` cutoff. Rows with a missing required bar or
non-positive scale abstain rather than being imputed or bridged across sessions.

This normalized outcome describes a move unusual relative to the stock's recent observed regime,
while remaining comparable across prices and tickers.

## Secondary outcomes

These values are retained for later robustness analysis and are not mixed into the v1 label:

```text
next_abs_log_return = abs(ln(C_{t+1} / C_t))
next_high_low_log_range = ln(H_{t+1} / L_{t+1})
next_parkinson_volatility = abs(ln(H_{t+1} / L_{t+1})) / sqrt(4 * ln(2))
```

## Train-only candidate threshold

M2 uses the linearly interpolated 90th percentile of eligible **training** primary outcomes:

```text
HIGH_RISK if primary_outcome >= train_quantile_0.90
NORMAL otherwise
```

The 90th percentile creates a meaningful but non-dominant high-risk class without looking at
validation or test prevalence. It is a versioned candidate, not a universal financial constant.
M6 may compare a predeclared alternative using train/validation only; any change requires a new
artifact and must occur before sealed-test opening.

The threshold artifact records the market snapshot hash, protocol-config hash, fit period, fit row
count, quantile method, numerical threshold, and explicit zero validation/test rows used.

## Split and sealing policy

- Training threshold inputs require both `t` and `t+1` inside training.
- Validation rows require both sessions inside validation.
- Cross-boundary rows are excluded.
- M2 materializes only train and validation rows.
- Sealed-test outcomes and labels are not generated, summarized, or inspected in M2.
- M7 may materialize test once after model, preprocessing, feature list, target protocol,
  calibration, and decision threshold are frozen.

The public M2 report may disclose training threshold and prevalence. It must not contain validation
label distribution or any test outcome.

## Leakage tests

Automated tests establish that:

- changing validation `t+1` changes its outcome/label but not the `t` state hash or numerical
  train-only threshold;
- a missing immediate target session is not replaced by a later price;
- train, validation, and test cannot overlap through target sessions;
- tampered M1 snapshots fail SHA-256 verification;
- artifacts cannot silently overwrite different existing content;
- M2 configuration cannot request sealed-test materialization.

No manual annotation, sentiment truth, LLM judgment, private holding, or trading rule participates.
