# M3 Market-Only Risk Features — Raw-Free Audit Summary

Audit date: 2026-08-27  
Pipeline: `risk-features-v1`  
Result: **PASS**

## Materialized dataset

- Feature count per row: 23.
- Training rows: 23,890.
- Validation rows: 4,800.
- Null feature values: 0.
- Non-finite feature values: 0.
- Rows abstained for incomplete 35-session consecutive history: 2,100.
- Preprocessing fitted: **false**.
- Models trained: **false**.
- Validation label distribution inspected: **false**.
- Sealed-test features materialized: **false**.
- Sealed-test outcomes inspected: **false**.

The 2,100 abstentions are primarily the explicit downstream effect of provider-versus-benchmark
session gaps already recorded in M1. No price or feature was fabricated, forward-filled, or bridged
across a missing session. Every ticker still passed the predeclared minimum of 2,200 training and
350 validation feature rows.

## Groups

- Price: 7.
- Volume: 3.
- Volatility/range: 5.
- Compact technical: 3.
- TAIEX market context: 5.

No news, sentiment, announcement, LLM, portfolio, or private-user field participates in M3.

## Lineage

- M1 market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`.
- M2 risk-label dataset SHA-256:
  `e15c09cacd68eb85fabcc33d7e704cc0d1cdf7998138196dcfd038792e91682a`.
- M3 config SHA-256:
  `cf57d71992b2f097217b6b7d9bafcaad742e7def2df176f532ec25f72da7c02e`.
- M3 risk-feature dataset SHA-256:
  `a9898ce18a2497efaa98d22dc5e99f40bae446f175781c3c47bde92972d26bb0`.

Detailed feature/target rows and the machine report remain in Git-ignored `.tools/` and
`artifacts/` paths. This public summary contains no raw provider rows, validation label statistics,
test outcome, credential, personal information, or private holding.

M4 may now fit naive and Logistic Regression baselines using training-only preprocessing and use
validation solely for model/decision evaluation. Test remains sealed.
