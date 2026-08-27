# F2 Historical Dataset Rebuild Result

Status: **COMPLETE WITH DOCUMENTED SOURCE-COVERAGE WARNING**

Dataset version: `final-volatility-surprise-dataset-v1`

Dataset SHA-256:
`2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c`

## Lineage

- Frozen F1 config SHA-256:
  `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66`.
- Market dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`.
- Feature config SHA-256:
  `cf57d71992b2f097217b6b7d9bafcaad742e7def2df176f532ec25f72da7c02e`.
- Feature pipeline: `risk-features-v1`, fixed 23-feature contract.
- Target: `next_session_stock_normalized_abs_log_return_v1`.
- Local immutable dataset:
  `.tools/datasets/final-volatility-surprise-dataset-v1/dataset.json` (Git ignored).
- Local machine audit: `artifacts/f2-final-study-dataset-audit.json` (Git ignored).

No preprocessing was fitted, no model was trained and no binary label was materialized.

## Coverage and reconciliation

- Candidate ticker/session rows: 38,290.
- Eligible rows: 32,357.
- Excluded rows: 5,933.
- Eligible feature dates: 2011-01-03–2026-08-25.
- Eligible target dates: 2011-01-04–2026-08-26.
- Duplicate `(ticker, feature_session)` identities: 0.
- Target/future fields in the fixed feature mapping: 0.

Exclusions reconcile exactly to candidates:

| Reason | Count |
| --- | ---: |
| Missing consecutive 35-session feature bar | 5,756 |
| Missing immediate target bar | 167 |
| No later benchmark session after the final observed session | 10 |
| Near-zero/non-finite trailing volatility | 0 |
| Null/non-finite feature | 0 |
| Total | 5,933 |

Missing bars were not imputed, forward-filled or replaced by later provider rows.

## Ticker coverage

| Ticker | Candidate | Eligible | Excluded |
| --- | ---: | ---: | ---: |
| 0050 | 3,829 | 3,267 | 562 |
| 1301 | 3,829 | 3,232 | 597 |
| 1303 | 3,829 | 3,233 | 596 |
| 2308 | 3,829 | 3,232 | 597 |
| 2317 | 3,829 | 3,232 | 597 |
| 2330 | 3,829 | 3,232 | 597 |
| 2412 | 3,829 | 3,232 | 597 |
| 2454 | 3,829 | 3,233 | 596 |
| 2881 | 3,829 | 3,232 | 597 |
| 2882 | 3,829 | 3,232 | 597 |

## Frozen outer-fold coverage

These are row counts only. F2 did not fit or evaluate any model.

| Outer fold | Training rows | Evaluation rows |
| --- | ---: | ---: |
| `outer_2017_2018` | 11,710 | 3,420 |
| `outer_2019_2020` | 15,140 | 4,220 |
| `outer_2021_2022` | 19,350 | 4,540 |
| `outer_2023` | 23,890 | 2,390 |
| `outer_2024` | 26,280 | 2,420 |
| `outer_2025` | 28,700 | 2,106 |
| `outer_2026_partial` | 30,806 | 1,541 |

## Source-coverage warning

Eighteen benchmark sessions have missing stock bars for at least two tickers. Sixteen historical
sessions are absent for all ten tickers; the dates include Saturday make-up sessions and one
provider/benchmark calendar mismatch on 2021-04-06. Two recent cases require explicit attention:

- 2025-08-01: stock bars are missing for nine tickers (all except 0050). Under the frozen strict
  35-session contract this removes the missing target row and later rows whose lookback crosses
  that gap, explaining the smaller 2025 evaluation count for those tickers.
- 2026-08-26: eight tickers lack a stock bar in the bounded market snapshot. This is also the final
  benchmark session, so no row can use it as a feature date because `t+1` is unavailable.

The full machine-readable list is retained in the ignored audit report. F2 does not silently repair
these gaps. F3 must preserve the exclusion behavior while auditing feature availability and may
only change calendar/provider policy through a separately versioned, pre-model decision.

## Safety result

- Exact next benchmark-session target: enforced.
- `t+1` mutation changes target but not the same row's feature hash: tested.
- Unique ticker/date identity: enforced.
- Frozen market/F1/feature-config lineage: enforced.
- Deterministic rebuild: same dataset SHA on repeated execution.
- Random split, preprocessing and training: absent.
- Raw provider rows, secrets and private holdings in this report: absent.

F2 stops here. F3 has not started.
