# F11B-2 Current-market Gate Audit

Status: **COMPLETE / BLOCKED — 2 PASS, 7 BLOCKED / F11B-2 NOT STARTED**  
Date: 2026-08-29  
Machine contract: `f11b-current-market-gate-audit-v1`

## Decision

The nine frozen prerequisites were audited before any current-market integration. Only the TAIEX
source and timezone gates pass. F11B-2 cannot start, and the controlled F11B-1B route must not be
promoted to live/current output.

| Gate | Result | Finding |
| --- | --- | --- |
| Current OHLCV source | BLOCKED | Yahoo returned usable rows, but the chart endpoint's formal current-serving documentation/credential boundary was not verified; 0050 also lacked the latest benchmark session. |
| TAIEX source | PASS | FinMind officially documents `TaiwanStockTotalReturnIndex/TAIEX`; bounded data reached 2026-08-28. |
| Exact 23-feature parity | BLOCKED | Historical builder exists; no separately validated current materializer exists. |
| Cutoff semantics | BLOCKED | Historical 13:30 cutoff conflicts with current TAIEX's documented approximately 16:50 availability. |
| Timezone | PASS | Existing configuration/provider normalization uses `Asia/Taipei`. |
| Missing-data rules | BLOCKED | The 0050 gap demonstrates the need for a frozen exact-session abstention/staleness rule. |
| Training/inference parity | BLOCKED | No current feature package has been compared against historical `risk-features-v1` rows. |
| Lineage | BLOCKED | No current normalized stock/benchmark snapshot and feature manifest exists. |
| Validation | BLOCKED | F11B-1B fixture tests are not current-market validation. |

## Bounded source evidence

The read-only probe covered 2026-05-01 through 2026-08-29 and retained no raw response or price.
FinMind returned 83 benchmark sessions through 2026-08-28. Nine of ten frozen tickers had all 35
latest benchmark sessions in Yahoo's normalized response. `0050` stopped at 2026-08-27, had one
missing required session and emitted one provider warning. The system must abstain rather than use
an older session silently.

A separate one-ticker, one-month entitlement probe of FinMind's officially documented
`TaiwanStockPriceAdj` returned HTTP/API status 400 with zero rows in the current environment. The
documentation marks that adjusted-price dataset as Backer/Sponsor-only. No response message or raw
payload was retained. It is therefore not an immediately available replacement for Yahoo.

FinMind's official documentation states that `TaiwanStockTotalReturnIndex` covers 2003 onward and
is normally updated weekdays at 16:50, with the API's actual availability controlling. Its quick
start documents 300 unauthenticated or 600 token-authenticated requests per hour. Yahoo's general
API terms make access revocable and require compliance with API-specific documentation and
credentials; this audit did not establish a formally documented/current-serving contract for the
chart endpoint used by the historical adapter. Successful HTTP access alone is not a licensing or
production-readiness decision.

## Required remediation order

1. Adopt an explicitly permitted OHLCV source that provides the frozen adjusted-close semantics,
   or obtain/record formal permission for the current source.
2. Freeze separate `feature_session_close` and `data_available_at` fields; do not call 13:30 data
   available when the benchmark arrives around 16:50.
3. Freeze exact-session abstention and staleness rules; never backfill 0050 silently.
4. Implement a current materializer by reusing the frozen formulas, then prove exact 23-feature
   parity on historical rows.
5. Create checksummed normalized source/feature manifests and an end-to-end offline validation.
6. Re-run all nine gates. Only a 9/9 result may authorize F11B-2 implementation.

No live GAS, webhook, trigger, portfolio, provider schedule or deployment was changed.
