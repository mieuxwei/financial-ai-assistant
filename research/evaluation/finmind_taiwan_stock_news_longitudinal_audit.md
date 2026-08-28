# FinMind `TaiwanStockNews` Longitudinal Audit

Audit date: 2026-08-28  
Protocol: `finmind-news-longitudinal-audit-v1`  
Decision: **CONDITIONAL for deduplicated title-level intelligence; HOLD for direct
market-reaction weak supervision**

## Question and boundary

This audit tests the fixed ten-ticker research universe—0050, 1301, 1303, 2308, 2317, 2330,
2412, 2454, 2881 and 2882—across the pre-sealed-test years 2018–2024. It asks:

1. how much historical data the API actually returns;
2. whether timestamps, missingness and duplicates are suitable for chronological research; and
3. whether the returned text has enough information for market-reaction weak-supervision input.

It does not use 2025–2026, inspect market outcomes, train a model, generate sentiment truth or use
manual review. Raw API responses are cached only under ignored `.tools/`; the committed code and
this report contain aggregate statistics and hashes, not titles, descriptions or links.

## API feasibility finding

The current official v4 endpoint rejects `end_date` for `TaiwanStockNews` and states that the
dataset is too large to return more than one day. Omitting `data_id` requires a paid account. The
old official v3 range example is no longer executable: the v3 endpoint returned `Not Found`.

Primary documentation: [TaiwanStockNews](https://finmind.github.io/en/tutor/TaiwanMarket/Others/),
[API request contract and limits](https://finmind.github.io/en/quickstart/), and
[FinMind terms/data-licence boundary](https://finmind.github.io/en/PrivacyPolicy/).

A complete 2018–2024 ten-ticker daily census would therefore require 25,570 requests. At the
documented anonymous 300 requests/hour it has a theoretical lower bound of 85.2 hours; a registered
600 requests/hour token still implies 42.6 hours, before retries. Bursting around this limit was
not attempted.

The frozen bounded design instead samples four deterministic Wednesdays per year—one in February,
May, August and November—for every ticker. This gives 280 requests spanning the full seven-year
period while staying inside one anonymous hourly allowance. It is a **stratified longitudinal
sample, not a full-period census**, so 1,547 is the exact retrieved sample count, not the total
number of all historical articles.

## Reproducibility

- Config: `research/configs/finmind_news_longitudinal_audit.v1.json`
- Runner: `research/evaluation/finmind_news_longitudinal_audit.py`
- Ignored aggregate artifact: `artifacts/finmind-news-longitudinal-audit.json`
- Ignored local cache: 280 response files, approximately 1.6 MB
- Config SHA-256: `aa4420b88e0ff3e79ea196a11481c89665b0e98a7d4e56e375bb92a4f80f19ba`
- Aggregate artifact SHA-256: `a0d9d9b81eca69055978c685465d3a0cc97651adaf2ea41c7c739a9b9ca954fa`
- Request-lineage SHA-256: `1bd24cff8266eaf4b234bd4949c4954df4e60743beb21f76244a3418ce038aa6`

All 280 planned requests completed. The second deterministic run used the local cache and reproduced
the same counts without another network request.

## 1. Coverage actually observed

The 280 requests returned 1,547 rows. Only 136 sampled ticker-days were non-empty (48.6%).

| Year | Requests | Non-empty ticker-days | Records |
| ---: | ---: | ---: | ---: |
| 2018 | 40 | 0 | 0 |
| 2019 | 40 | 0 | 0 |
| 2020 | 40 | 5 | 8 |
| 2021 | 40 | 33 | 316 |
| 2022 | 40 | 31 | 454 |
| 2023 | 40 | 35 | 404 |
| 2024 | 40 | 32 | 365 |

The zero result on all 80 sampled 2018–2019 ticker-days and the very sparse 2020 sample are strong
coverage warnings. They do not prove that every unqueried day is empty, but they make a balanced
2018–2024 news panel implausible without a full census or a separate archive.

| Ticker | Requests | Non-empty days | Records | First sampled year with data | Last |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0050 | 28 | 8 | 55 | 2021 | 2024 |
| 1301 | 28 | 12 | 48 | 2020 | 2024 |
| 1303 | 28 | 6 | 16 | 2021 | 2024 |
| 2308 | 28 | 13 | 116 | 2021 | 2024 |
| 2317 | 28 | 16 | 383 | 2021 | 2024 |
| 2330 | 28 | 16 | 441 | 2021 | 2024 |
| 2412 | 28 | 18 | 127 | 2020 | 2024 |
| 2454 | 28 | 17 | 141 | 2020 | 2024 |
| 2881 | 28 | 16 | 130 | 2021 | 2024 |
| 2882 | 28 | 14 | 90 | 2021 | 2024 |

Coverage is heavily concentrated in high-news-volume names: 2317 and 2330 jointly account for 824
of 1,547 rows (53.3%), while 1303 has only 16. Any future NLP feature experiment must report
coverage and missingness by ticker/year rather than treating no-news rows as equivalent across
the universe.

## 2. Timestamp, missingness and duplicate quality

- 100% of returned timestamp strings parsed with `datetime.fromisoformat`.
- 100% had the same calendar date as the requested API day.
- 0% carried a UTC offset or timezone identifier.
- 0.19% were exactly midnight; most rows therefore contain an intraday-looking clock time.
- The API documentation still does not define whether `date` is publisher time, crawler ingestion
  time or a later normalization time.
- One stable live schema was observed, but it omitted the documented `description` field.
- Canonicalized exact-link duplicates were 390/1,547 (25.21%).
- Exact-title duplicates were 317/1,547 (20.49%).

The strings are mechanically parseable, but **parseability is not event-time provenance**. With no
timezone and no publication-versus-ingestion contract, the time cannot safely decide whether an
article was available before the Taiwan market close. The duplicate rate also requires canonical
article grouping while preserving the many-to-many article–ticker mapping.

## 3. Information sufficiency

- Non-empty title rate: 100%.
- Non-empty description rate: 0%; the documented field did not appear in any of 1,547 rows.
- Median title/combined cleaned length: 38 characters.
- Combined cleaned length p10/p90: 26/55 characters.
- 81.71% pass the frozen title-level rule of at least 10 title characters and 30 combined
  characters.

The title-level gate passes. These rows can support bounded, deduplicated features such as ticker
matching, title keywords, named entities, embeddings, related-event retrieval and a simple
news-count/novelty signal. The rich-text gate fails: there is no summary/body field, one fifth of
titles are exact duplicates, and the median input is only 38 characters. This is not enough to
claim robust article-level sentiment, causal event interpretation or human-validated semantic
labels.

## Decision

1. **CONDITIONAL — title-level intelligence.** FinMind may be used for pre-2025 discovery and
   deduplicated title-level features after coverage flags, link/title canonicalization, publisher
   rights minimization and an explicit missing-news indicator.
2. **HOLD — direct market-reaction weak supervision.** Timestamp semantics/timezone, 2018–2020
   coverage, duplicate grouping and underlying publisher rights remain unresolved. The rows must
   not become ground-truth sentiment or same-session reaction labels.
3. **HOLD — rich-text NLP training.** The live response contains no description/body. Do not crawl
   linked publishers to fill it without a separate source-by-source licence and robots audit.
4. **No sealed-test impact.** The audit ends in 2024 and reads no market target or old classifier
   evaluation.

## Safest next experiment

The non-blocking F9 experiment may use only deduplicated title-derived features from 2021–2024,
with conservative availability: treat a FinMind row as usable no earlier than the next exchange
session after its calendar date. This avoids same-day cutoff leakage but no longer measures an
immediate event reaction. The market-only model remains primary, and a null NLP increment remains
acceptable.

For genuine event-reaction weak supervision, official MOPS/TWSE announcement timestamps remain the
preferred source. Before a FinMind daily census, first obtain written timestamp semantics and a
permitted bulk/all-market access path; otherwise the resumable runner can execute slowly under the
published limit, but completion is operationally expensive and does not solve the missing-text or
rights problems.
