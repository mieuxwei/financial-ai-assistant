# M8 Historical Official-Event Backfill Audit

Date: 2026-08-26  
Decision: HOLD for automated historical backfill; ACCEPT for forward daily collection

## Scope

This audit asks whether an official, documented source can populate pre-2025 train and 2025
validation events with reliable publication dates and times. It does not download event text,
inspect sealed reaction targets, use private data or evaluate Eland.

## Official evidence

1. The [TWSE OpenAPI catalogue](https://openapi.twse.com.tw/) documents
   `/v1/opendata/t187ap04_L` as **上市公司每日重大訊息**. Its documented operation exposes the
   current daily dataset and no historical date-range parameters.
2. The [Government Data Platform record](https://data.gov.tw/en/datasets/18415) describes the same
   dataset as daily, updated every day, and licensed under Open Government Data Licence v1. It lists
   announcement date/time, company code, subject, clause, fact date and description, but only links
   the current CSV/OpenAPI resource.
3. The [official MOPS site](https://mops.twse.com.tw/) visibly offers an interactive historical
   material-information search. However, no documented bulk/API contract was found for that
   interface, and direct historical query URLs can be redirected to the MOPS security error page.

## FinMind bounded historical metadata check

The raw-free `finmind-news-metadata-audit-v1` runner queried ticker `2330` on three predeclared
single dates. It retained only aggregate schema, timestamp-format and duplicate-link-hash counts:

- 2020-04-01 returned zero rows despite appearing in the documentation example;
- 2024-04-01 returned nine rows and 2025-04-01 returned 25 rows;
- both non-empty responses omitted the documented `description` field;
- all 34 timestamps were timezone-naive strings;
- two exact duplicate links occurred within the 2025 sample.

This confirms historical availability for some dates, but also demonstrates schema drift, uneven
coverage, duplicates and the unresolved timestamp contract. No title, description, URL or raw
response was saved in the report.

## Decision

- `t187ap04_L`: ACCEPT for idempotent forward daily collection and official metadata.
- Historical MOPS web query: HOLD for automated backfill. Do not reverse engineer, scrape around
  access controls, or treat an undocumented browser form as a stable research API.
- FinMind news: remains CONDITIONAL for discovery metadata and HOLD as a reaction-event source.
  The bounded audit failed the schema gate and cannot establish publication-time semantics or
  timezone; underlying publisher rights and cross-publisher duplicates also remain unresolved.
- Current M8 all-test snapshot: retain as engine evidence only; do not use it for selection or
  training.

## Safe continuation paths

1. Run scheduled daily ingestion going forward, preserving UTC publication timestamps, source IDs,
   content/title hashes and immutable ingestion-run evidence.
2. Request or locate a documented official historical export/API with explicit reuse terms. Audit
   schema, timezone semantics, coverage, corrections, duplicates and licence before download.
3. If a licensed third-party archive is considered, create a separate source-manifest decision. It
   must pass provenance, original-publisher rights, temporal lineage, duplicate and split-leakage
   gates before any backfill.

Until a path passes, `historical_train_validation_ready` remains `false`, M8 stays engineering-
complete/data-incomplete, and reaction-target threshold selection and M11 training remain blocked.
