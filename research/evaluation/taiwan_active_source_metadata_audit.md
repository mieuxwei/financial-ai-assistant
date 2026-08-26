# Taiwan Active Source Metadata Audit — M6

Audit date: 2026-08-26  
Scope: metadata, public documentation, read-only API checks and the approved FSC archive audit
Excluded: committed raw text, training, weak-label generation and backtesting

## Decision summary

| Source and purpose | Decision | Current finding |
| --- | --- | --- |
| TWSE OpenAPI `t187ap04_L` for official disclosure ingestion and structured metadata | `ACCEPT` | Official endpoint is live without credentials and exposes announcement date/time, company code, title, disclosure clause, fact date and explanation. |
| TWSE disclosure text for domain-adaptive training | `CONDITIONAL` | Training/redistribution must be limited to records whose open-data status, attribution and retention scope are documented; website content outside government-open-data authorization is not automatically reusable. |
| `lianghsun/tw-finance-159M` for domain adaptation | `HOLD` | Dataset card is public, files are gated, licence is CC BY-NC-SA 4.0, underlying publisher rights remain unresolved, and `updated_at` does not establish publication-time lineage. |
| FinMind `TaiwanStockNews` for discovery and metadata | `CONDITIONAL` | Anonymous single-stock/day request succeeded and returned timestamp, ticker, source, title and link; source quality is mixed, duplicates exist, timezone semantics and underlying publisher rights remain unresolved. |
| FinMind `TaiwanStockNews` as direct reaction-label event source | `HOLD` | Do not use until timestamp timezone/meaning, duplicate grouping and publication-versus-ingestion semantics are verified. |
| FinMind `TaiwanStockTotalReturnIndex` / `TAIEX` as research benchmark | `ACCEPT` | Anonymous bounded request succeeded; official documentation describes a free total-return series with `price`, `stock_id` and `date`, available from 2003. Acceptance is for this non-commercial research purpose only. |
| Official FSC law archives for optional domain adaptation | Purpose-specific `ACCEPT` | Five checksummed official archives and 6,047 XML records passed automated structure audit. Only filtered, deduplicated, non-commercial unlabelled adaptation feasibility is accepted; labels, redistribution and deployment are not. |
| `lianghsun/tw-fsc` derived OCR/VLM corpus | `HOLD` | Gated 2.23 GB derived corpus; OCR, inline HTML, page images, LLM-generated table descriptions/categories and source-level licence scope require audit before any text-only use. |

Eland is not included because it is excluded from the active modeling pipeline and requires no
further audit.

## 1. `tw-finance-159M`

Primary evidence: [`lianghsun/tw-finance-159M` dataset card](https://huggingface.co/datasets/lianghsun/tw-finance-159M).

Verified metadata:

- Traditional Chinese Taiwan finance/industry/news corpus, approximately 159M tokens and 470 MB.
- Dataset-level licence is `CC-BY-NC-SA-4.0`; file access requires accepting a gated-access
  condition.
- Rows are documented with `text`, `token_count`, `word_count`, `url` and `updated_at`.
- The dataset has no manual annotations and is proposed for continued/domain-adaptive pretraining.
- The documented domain includes finance, industry, property, social housing, personal finance,
  consumption and business activity; the card warns of news releases and advertorial content.
- The card itself warns that commercial use requires evaluation of original-report copyright.

Unresolved gates:

- dataset-level licensing does not prove the right to reproduce or train on every publisher's full
  article;
- `updated_at` is insufficient for strict publication-time splitting unless its semantics are
  established;
- record/source distributions, exact/near duplicates, syndication, temporal range, PII and domain
  purity cannot be audited without approved access to the files;
- share-alike obligations for any released model/artifact require a separate release-policy review.

Decision: remain `HOLD`. Do not request access or download 470 MB during this milestone without
explicit user approval. If approved later, the first operation is a streaming aggregate audit, not
training.

## 2. MOPS / TWSE official disclosures

Primary evidence:

- [TWSE OpenAPI catalogue](https://openapi.twse.com.tw/), which identifies
  `/v1/opendata/t187ap04_L` as listed-company daily material information;
- [TWSE terms of use](https://wwwc.twse.com.tw/zh/terms/use.html), which restrict general website
  reuse but exempts TWSE data authorized through the government open-data platform.

A live, anonymous read-only request to the existing endpoint succeeded on the audit date. The
response exposed ROC-format output/announcement/fact dates, announcement time, company code/name,
title, disclosure-clause code and explanation. No response body was saved by this audit.

Purpose-specific decisions:

- `ACCEPT` for official ingestion, source traceability, ticker identity, timestamp construction and
  official disclosure-category metadata.
- `CONDITIONAL` for domain-adaptive training. Before retaining explanations as a corpus, pin the
  exact open-data dataset identity and licence/attribution notice, minimize public artifacts to
  hashes/aggregates, and apply automated PII/markup quality rules.

The endpoint's `發言日期` + `發言時間` is the event-time candidate. `事實發生日` is event metadata
and must never replace the publication timestamp. ROC calendar conversion, zero-padded time
parsing, correction grouping and repeated multi-month notices require deterministic tests.

## 3. FinMind news and benchmark data

Primary evidence:

- [FinMind project licence statement](https://github.com/FinMind/FinMind/blob/master/README.md),
  which limits provided content to educational, non-commercial use;
- [FinMind TaiwanStockNews documentation](https://finmind.github.io/tutor/TaiwanMarket/Others/);
- [FinMind total-return-index documentation](https://finmind.github.io/tutor/TaiwanMarket/Technical/).

Minimal anonymous smoke checks succeeded:

- `TaiwanStockNews`, one ticker and one day: response included timestamp-like `date`, `stock_id`,
  `link`, `source` and `title` fields.
- `TaiwanStockTotalReturnIndex`, `data_id=TAIEX`, five sessions: response included `price`,
  `stock_id` and `date` with status 200.

The news sample showed mixed publisher and forum sources plus repeated/syndicated links. The API
documentation and schema do not specify a timezone field, so the timestamp must not yet drive the
13:30 cutoff. Underlying publisher terms are not inherited automatically from FinMind's software
or project licence.

Decisions:

- News is `CONDITIONAL` for discovery, link/source metadata and coverage studies, but `HOLD` as a
  direct market-reaction event source until timezone, timestamp semantics, duplication and rights
  gates pass. Do not retain or redistribute underlying full article content.
- `TaiwanStockTotalReturnIndex` with `data_id=TAIEX` is the selected primary broad-market total-return
  benchmark for non-commercial research. Pin API dataset ID, source terms, request range and
  response snapshot hash when implemented. Re-audit before any commercial/public product use.
- `TPEx` is a later secondary benchmark for OTC securities; it must not be mixed with TAIEX without
  an explicit universe mapping.

## 4. FSC / regulatory corpus

Primary evidence:

- [FSC website open-data declaration](https://esg.fsc.gov.tw/SinglePage/Declare/) applies the Taiwan
  Government Open Data Licence v1 to covered material with attribution, while excluding specially
  identified third-party/special works and rights outside copyright;
- [`lianghsun/tw-fsc` dataset card](https://huggingface.co/datasets/lianghsun/tw-fsc) describes a
  gated 2.23 GB page-level image/OCR corpus derived from FSC documents.

The third-party `tw-fsc` corpus is not equivalent to a clean official-text mirror. It contains page
images, OCR output, inline table markup, automatically generated descriptions/tags/categories and
document-version risks. Its automated labels are not ground truth.

Decision: keep the derived `tw-fsc` corpus on `HOLD`. The separate official FSC archives have now
passed an approved, raw-free automated audit and are purpose-specifically `ACCEPT` for a filtered,
deduplicated, non-commercial unlabelled domain-adaptation feasibility corpus. The audit found 6,047
records, no exact or cross-agency content duplicates, 14 within-agency duplicate-content extra
rows, ten unparseable publication dates and one empty content record. The latter records must be
excluded as applicable; attachments and special/third-party works remain forbidden. Full findings
and mandatory filters are in `research/evaluation/fsc_official_archive_audit.md`.

## Source manifest gate delivered

The versioned manifest is `research/configs/taiwan_active_sources.v1.json`; the runner is
`research/evaluation/source_manifest.py`. A live run on 2026-08-26 passed both sources:

- TWSE: HTTP 200, 101 records, all nine required fields present;
- FinMind TAIEX: HTTP 200, five sessions from 2026-08-03 through 2026-08-07, all three required
  fields present;
- both observations include schema and response snapshot SHA-256 values;
- `raw_content_stored` is `false`, and the report contains no title, explanation or price rows.

The generated report belongs at `artifacts/taiwan-source-gate-report.json` and is ignored by Git.

This unit requires no model training, manual labels, paid LLM, Eland work or large data download.

## FSC content-audit unit completed

The bounded FSC official-source manifest is now implemented at
`research/configs/fsc_official_sources.v1.json`. Its HEAD-only live gate passed all five official
archives on 2026-08-26 without downloading their bodies:

| Archive | Content length |
| --- | ---: |
| FSC commission | 224,273 bytes |
| Banking Bureau | 2,217,525 bytes |
| Securities and Futures Bureau | 2,661,534 bytes |
| Insurance Bureau | 2,054,245 bytes |
| Financial Examination Bureau | 67,102 bytes |
| **Total** | **7,224,679 bytes** |

All endpoints returned HTTP 200, `application/x-zip-compressed`, `Content-Length`, `Last-Modified`
and `ETag`; the gate retained only header/schema hashes and stored no archive content.

The user approved the bounded download. The archives remain only in ignored
`.tools/datasets/fsc-official/`; their exact sizes and SHA-256 values are pinned in
`research/configs/fsc_official_archive_snapshot.v1.json`. The automated runner
`research/evaluation/fsc_archive_audit.py` passed all five archives and emitted only aggregate
statistics and hashes to the ignored artifact report. This satisfies the M6 purpose-specific corpus
gate. The subsequent M7 builder retained 6,021 family-isolated records. The two-candidate,
two-step CPU feasibility passed, followed by an explicitly approved 200-step bounded pilot. The
pilot kept test sealed and weights ignored; it recommends BERT-base-Chinese for frozen
representation only. Any larger/full-corpus run remains a separate future decision.
