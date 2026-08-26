# M1 Risk Market Dataset Protocol

## Status and boundary

This document defines the new Track A M1 market dataset. M1 builds and audits an immutable
price/volume snapshot only. It does **not** generate abnormal-volatility labels, train a model,
inspect sealed-test outcomes, or use NLP features.

The machine-readable configuration is
`research/configs/risk_market_dataset.v1.json`. Generated rows remain under the Git-ignored
`.tools/datasets/risk-market-dataset-v1/` directory. The generated audit report remains under the
Git-ignored `artifacts/` directory so raw dates or provider data cannot be published accidentally.

## Universe

The fixed research universe contains ten liquid, long-history Taiwan-listed representatives:
0050, 1301, 1303, 2308, 2317, 2330, 2412, 2454, 2881, and 2882. The universe is fixed before
label construction and modeling. It is a bounded research sample, not a claim of full-market
coverage or an investment recommendation.

## Time contract

- snapshot and warm-up start: 2010-01-01;
- training period: 2011-01-01 through 2022-12-31;
- validation period: 2023-01-01 through 2024-12-31;
- sealed test period: 2025-01-01 through 2026-08-26;
- timezone: Asia/Taipei.

The test interval is stored so later milestones can reproduce features and labels, but M1 reports
only structural coverage and integrity metadata. It does not calculate or disclose test-period
label prevalence, model metrics, threshold performance, or trading outcomes.

## Sources and reproducibility

- Stock OHLCV: Yahoo Finance prototype provider through the existing ingestion adapter.
- Exchange-session reference and market context: FinMind `TaiwanStockTotalReturnIndex`, `TAIEX`.

Both are third-party research sources and remain subject to their terms, corrections, and service
availability. The dataset snapshot records source identifiers, configured terms URLs, normalized
rows, split membership, and SHA-256 hashes. A different payload cannot silently overwrite an
existing snapshot.

The 2026-08-27 terms review does not establish a right to redistribute raw provider data. FinMind's
current terms prohibit raw-data redistribution or a mirror service outside the applicable plan,
and the Yahoo chart source remains a prototype provider with revocable/changeable service terms.
Consequently, raw rows and generated machine reports stay local and Git-ignored; the repository
publishes only code, configuration, hashes, aggregate audit facts, and source attribution.

## Quality gates

The audit fails on any of the following:

- unexpected stock source, duplicate ticker/date, duplicate benchmark date, or invalid hash;
- non-positive price, invalid OHLC range, or negative volume;
- missing-session ratio above 3% against the benchmark session calendar in any split;
- fewer than 200 warm-up, 2,500 training, 450 validation, or 300 sealed-test observations for any
  configured ticker.

Zero-volume observations are counted but not silently removed. Dates present in stock data but not
in the benchmark reference are hashed and counted for investigation. Missing-date identities are
also represented only by counts and hashes in the report.

## Leakage controls

- Universe, periods, and gates are configuration-controlled before M2 label design.
- Splits are chronological and disjoint.
- No imputation, scaling, threshold fitting, feature selection, or label construction occurs here.
- `sealed_test_outcomes_inspected`, `risk_labels_generated`, and `models_trained` must all remain
  `false` in the M1 dataset and audit report.
- The audit report contains no secrets, holdings, manual labels, or raw market rows.

M2 may define risk targets only after this M1 structural audit passes.
