# F11B-2A Official Current-Market Source & Feature-Parity Result

Status: **COMPLETE — current-market integration remains gated**

Decision code:
`OFFICIAL_OHLCV_AVAILABLE_BUT_ADJUSTED_PARITY_UNRESOLVED`

This was a bounded, read-only source and serving-parity audit. It did not train or retune a
model, alter the target or 23-feature contract, modify GAS, deploy, or begin F11B-2.

## Executive decision

The official TWSE route covers all ten frozen instruments and supplied all of the most recent
35 exchange sessions through 2026-08-28. The TAIEX total-return benchmark is also equivalent:
the existing FinMind `TaiwanStockTotalReturnIndex/TAIEX` values exactly matched TWSE's official
`TAIEXTotalReturnIndex` on all 20 shared current sessions.

That is not enough to approve current inference. The frozen stock snapshot was built from
Yahoo chart data, and its `adjusted_close` is specifically the provider's `adjclose` field.
The audited TWSE OpenAPI contains a current ex-right/ex-dividend preview, but no historical
corporate-action endpoint that proves a deterministic reconstruction is semantically identical
to Yahoo `adjclose`. Raw OHLCV is not source-identical either. The exact feature audit therefore
passes only 5 of 23 features.

## Frozen contract discovered from repository artifacts

- Frozen universe: 0050, 1301, 1303, 2308, 2317, 2330, 2412, 2454, 2881, 2882.
- All ten are TWSE instruments in the official current endpoint; no TPEx fallback is required.
- Historical stock source: Yahoo chart quote fields plus `indicators.adjclose`.
- Historical benchmark: FinMind `TaiwanStockTotalReturnIndex`, `data_id=TAIEX`.
- Feature pipeline: `risk-features-v1`, exact ordered 23-feature contract.
- Required history: 35 consecutive exchange sessions.
- Frozen feature output quantum: `0.000000000001`.
- Frozen research cutoff was 13:30 Asia/Taipei; it is not reused as a serving cutoff.

## Official current coverage

Exchange-session truth came from the audited TAIEX total-return sequence, not weekdays.

| ticker | market | official source | latest source session | latest exchange session | recent sessions | stale | usable |
|---|---|---|---|---|---:|---|---|
| 0050 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 1301 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 1303 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2308 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2317 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2330 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2412 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2454 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2881 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |
| 2882 | TWSE | STOCK_DAY_ALL | 2026-08-28 | 2026-08-28 | 35/35 | no | yes |

### 0050 resolution

TWSE returned 0050 for 2026-08-28 and the two official monthly windows contained all required
35 sessions. The earlier 0050 gap was therefore candidate-provider latency/freshness, not an ETF
symbol mapping or official TWSE coverage failure. A stale candidate row must never be relabeled as
current.

## Historical overlap and environment limitation

The intended overlap was 2024-01-01 through 2025-12-31. The bounded collection completed that
period for 0050, 1301 and 1303 and a partial period for 2308, yielding 1,483 aligned rows. TWSE then
returned HTTP 428 during the monthly collection. The adapter did not enter a retry loop; successful
normalized rows were retained only in ignored `.tools` storage.

HTTP 428 is recorded as an environment/rate-bound collection limit, not proof that the official
dataset lacks history. It does mean the ten-ticker historical parity evidence is incomplete. The
more fundamental adjusted-lineage failure is independent of that collection limit.

## Adjusted-price and corporate-action decision

The repository implementation proves only this historical meaning:

> `adjusted_close = Yahoo chart indicators.adjclose`, quantized to 0.001.

It does not contain an independently frozen declaration that this is precisely split-only,
dividend-adjusted, or a total-return price. The TWSE `TWT48U_ALL` OpenAPI response exposes current
fields such as cash dividend, stock dividend ratio, subscription terms and ex-dividend type. The
audited TWSE OpenAPI schema did not expose a historical corporate-action endpoint sufficient to
reconstruct and verify the complete 2024–2025 adjustment lineage.

Accordingly, an official adjusted series could be mathematically reasonable without being
training-equivalent. The adjusted-price parity statistics are deliberately null rather than
fabricated: no official reconstructed series passed the lineage prerequisite.

## Raw OHLCV parity

Normalization was frozen before comparison: prices in TWD at the repository's 0.000001 raw-price
quantum and volume in shares. No post-result tolerance relaxation was used.

| ticker | aligned rows | OHLC observation | volume observation |
|---|---:|---|---|
| 0050 | 480 | material corporate-action-scale divergence; max close difference 153.300002 | no exact rows; max difference 232,456,882 shares |
| 1301 | 484 | non-zero differences; max close difference 0.199998 | 1/484 exact; max difference 3,822,396 shares |
| 1303 | 484 | non-zero differences; max close difference 0.099998 | 1/484 exact; max difference 4,062,773 shares |
| 2308 | 35 | OHLC exact in bounded window | 0/35 exact; max difference 2,489,230 shares |
| remaining six | 0 historical overlap | not evaluated after bounded HTTP 428 stop | not evaluated |

This rejects raw training-source parity. In particular, the official transaction-day series and
the frozen Yahoo series cannot be silently substituted merely because both have fields named OHLCV.

## Exact 23-feature parity

`PASS` requires the predeclared 1e-12 frozen feature tolerance. `FAIL_NOT_EVALUABLE` means the
feature requires an official adjusted-close lineage that was not proven. The 1,245 comparisons
come from complete 35-session windows in the bounded overlap.

| feature | status | n | max abs diff | median abs diff | reason |
|---|---|---:|---:|---:|---|
| return_log_1 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| return_log_5 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| return_log_10 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| return_log_20 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| overnight_gap_log_1 | FAIL | 1,245 | 0.007026725147 | 0.000000025706 | raw OHLC differs |
| close_ma_deviation_5 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| close_ma_deviation_20 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| volume_log_change_1p_1 | FAIL | 1,245 | 5.037051261237 | 0.003425493780 | volume differs |
| volume_zscore_20 | FAIL | 1,245 | 1.890478178350 | 0.009928137047 | volume differs |
| zero_volume_flag | PASS | 1,245 | 0 | 0 | exact |
| volatility_log_return_5 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| volatility_log_return_20 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| high_low_log_range_1 | FAIL | 1,245 | 0.013538347889 | 0.000000027624 | raw OHLC differs |
| atr_14_normalized | FAIL | 1,245 | 0.000688279599 | 0.000000009652 | raw OHLC differs |
| parkinson_mean_5 | FAIL | 1,245 | 0.001626146505 | 0.000000008793 | raw OHLC differs |
| rsi_14 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| macd_12_26_normalized | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| macd_signal_9_normalized | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| benchmark_return_log_1 | PASS | 1,245 | 0 | 0 | benchmark equivalent |
| benchmark_return_log_20 | PASS | 1,245 | 0 | 0 | benchmark equivalent |
| benchmark_volatility_log_return_20 | PASS | 1,245 | 0 | 0 | benchmark equivalent |
| stock_minus_benchmark_return_log_1 | FAIL_NOT_EVALUABLE | 0 | — | — | adjusted close required |
| benchmark_drawdown_20 | PASS | 1,245 | 0 | 0 | benchmark equivalent |

Result: **5/23 PASS; exact training/serving feature parity FAILS.**

## Benchmark parity

Track A uses the TAIEX **total-return index**, not the price index. The FinMind current candidate
matched TWSE `MFI94U/TAIEXTotalReturnIndex` exactly on 20/20 shared sessions; maximum absolute
difference was 0.00. This benchmark identity must remain unchanged.

## Cutoff, freshness and missing-data contract

The historical 13:30 cutoff is not safe for current serving. FinMind documents weekday update
times around 16:50 for the total-return index and 17:30 for daily stock data. The conservative
candidate contract is therefore:

`SAFE_POST_CLOSE_AVAILABILITY = 18:00 Asia/Taipei`

Serving would additionally require every stock and benchmark
`latest_source_session == latest_exchange_session`. The clock alone is never sufficient.

Freshness gap is measured in audited exchange sessions. If the gap is positive, return
`ABSTAIN_CURRENT_DATA` or visibly stale status; never fall back silently. Current materialization
must use the frozen 35-session rule. No carry-forward or imputation is allowed; any missing required
stock or benchmark session causes abstention.

## Lineage contract

The candidate lineage is complete as a contract and includes ticker, market, endpoint/dataset,
retrieval time, source/exchange latest sessions, timezone, cutoff, corporate-action source,
benchmark source, feature version/SHA, stale status and abstention reason. This does not make the
underlying adjusted lineage equivalent. Raw provider payloads remain ignored and untracked.

## Nine-gate re-evaluation

| gate | result | reason |
|---|---|---|
| Current OHLCV source audited | PASS | official 10/10 current coverage and 35 sessions |
| TAIEX source audited | PASS | total-return identity; 20/20 exact current overlap |
| Exact 23-feature parity | FAIL | 5/23 pass |
| Cutoff semantics | PASS | conservative 18:00 plus session-equality rule frozen |
| Missing-data rules | PASS | no fill/carry-forward; explicit abstention |
| Training/inference feature parity | FAIL | adjusted lineage unresolved and raw features differ |
| Asia/Taipei timezone | PASS | frozen and retained |
| Current lineage | PASS | required candidate fields frozen |
| End-to-end validation | NOT RUN | cannot be inferred from source audit |

Updated result: **6/9 PASS**.

`next_action = NOT_READY_FOR_F11B_2`

F11B-2 current-market serving remains gated. The controlled research demo remains valid, and F12
portfolio finalization is not blocked by this result. The next executable unit is therefore F12,
not current-market E2E validation.

## Source references

- [TWSE OpenAPI](https://openapi.twse.com.tw/)
- [TWSE monthly STOCK_DAY](https://www.twse.com.tw/exchangeReport/STOCK_DAY)
- [TPEx OpenAPI](https://www.tpex.org.tw/openapi/swagger-ui/index.html)
- [FinMind Taiwan market technical data documentation](https://finmind.github.io/tutor/TaiwanMarket/Technical/)

