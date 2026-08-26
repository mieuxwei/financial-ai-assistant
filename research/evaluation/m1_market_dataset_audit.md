# M1 Market Dataset — Raw-Free Audit Summary

Audit date: 2026-08-27  
Result: **PASS**

## Frozen scope

- Universe: 0050, 1301, 1303, 2308, 2317, 2330, 2412, 2454, 2881, 2882.
- Warm-up/snapshot start: 2010-01-01.
- Train: 2011-01-01 through 2022-12-31.
- Validation: 2023-01-01 through 2024-12-31.
- Sealed test: 2025-01-01 through 2026-08-26.
- Stock source: Yahoo Finance prototype adapter.
- Benchmark/session reference: FinMind `TaiwanStockTotalReturnIndex`, `TAIEX`.

## Aggregate evidence

- Normalized stock rows: 40,691.
- Benchmark sessions: 4,080.
- Benchmark split sessions: warm-up 251, train 2,949, validation 481, sealed test 399.
- Per-ticker rows: 4,068–4,070.
- Per-ticker maximum missing-session ratio in any split: below 0.8%, versus the predeclared 3%
  rejection threshold.
- Fatal issues: 0.
- Dataset SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`.
- Benchmark snapshot SHA-256:
  `ca9da51710be06ca5560a302da34412b5fdf53dc5d0c38e46ffeacdd22eb31a5`.

The benchmark-versus-provider gaps include historical exchange-calendar/source discrepancies.
They are retained as hashed/countable missing observations rather than silently imputed. Zero
volume rows are counted and preserved for explicit M3 handling.

## Provider anomaly handled

Yahoo returned one impossible 0050 row on 2010-01-25 with a zero open while the other OHLC fields
were positive. The provider now quarantines structurally invalid rows and records a warning. A unit
test prevents regression. The resulting single missing observation remains visible in the audit;
it was not fabricated or manually repaired.

## Leakage and privacy assertions

- Sealed-test outcomes inspected: **false**.
- Risk labels generated: **false**.
- Models trained: **false**.
- Manual labels used: **false**.
- Raw market rows in this report: **false**.
- Secrets or private holdings in this report: **false**.

Raw provider data and the detailed machine audit remain under Git-ignored `.tools/` and
`artifacts/` paths. This summary is structural evidence only and contains no test-period target
distribution, model metric, trading result, token, credential, or personal portfolio data.

## Known limitations

- Yahoo and FinMind are third-party sources that can revise records or service behavior.
- The TAIEX total-return series is used as the session reference; it is not a separately sourced
  official exchange calendar.
- This audit does not claim permission to redistribute raw provider data.
- Corporate actions are represented by Yahoo adjusted close but are not independently reconciled
  against an official corporate-action ledger in M1.

M2 may now specify and test a train-only abnormal-risk label contract without opening sealed-test
outcomes.
