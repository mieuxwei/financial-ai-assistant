# M2 Risk Label Protocol — Raw-Free Audit Summary

Audit date: 2026-08-27  
Protocol: `next-session-volatility-risk-v1`  
Result: **PASS**

## Train-only threshold evidence

- Primary outcome: next-session normalized absolute log return.
- Trailing scale: 20 consecutive one-session adjusted-close log returns, population standard
  deviation (`ddof=0`), all available by session `t` close.
- Candidate threshold method: linear training quantile at 0.90.
- Eligible training rows: 25,990.
- Candidate threshold: `1.807988011793`.
- Training labels: 2,599 `HIGH_RISK`; 23,391 `NORMAL`.
- Training `HIGH_RISK` prevalence: 10.0%.
- Validation rows used to fit threshold: 0.
- Sealed-test rows used to fit threshold: 0.

The candidate is not a universal market constant. M6 may retain or replace it using only
predeclared train/validation evidence before M7, with a new artifact if changed.

## Materialization and quality evidence

- Materialized training rows: 25,990.
- Materialized validation rows: 4,800.
- Every ticker passed at least 2,500 training and 400 validation eligible rows.
- Validation label distribution inspected: **false**.
- Sealed-test rows materialized: **false**.
- Sealed-test outcomes inspected: **false**.
- Models trained: **false**.
- Manual labels used: **false**.
- Raw rows in this public report: **false**.

Rows abstain when the exact next benchmark session or any member of the required consecutive
20-return history is unavailable. They never jump across a missing session or silently impute an
outcome. Cross-split target rows are excluded.

## Lineage

- M1 market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`.
- M2 risk-label dataset SHA-256:
  `e15c09cacd68eb85fabcc33d7e704cc0d1cdf7998138196dcfd038792e91682a`.
- Train-only threshold artifact SHA-256:
  `7e2aa33fa705c0912358c9775bce05fac5c39cbfa24fae41a5ff50bdfe54aba7`.

Detailed rows and the machine audit remain under Git-ignored `.tools/` and `artifacts/` paths. No
raw market data, credentials, personal information, or private portfolio data appears here.

## Interpretation limit

`HIGH_RISK` means the realized next-session normalized absolute move crossed this train-derived
candidate threshold. It does not mean the price rose or fell, explain why it moved, recommend a
trade, or guarantee future behavior.

M3 may now build strictly `t`-available market features against this train/validation dataset.
