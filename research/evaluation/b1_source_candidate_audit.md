# B1 Source Candidate Audit

Audit date: 2026-08-29  
Protocol/manifest: `b1-source-candidate-manifest-v1`  
Decision: **PASS — B2 whitelist frozen; no training or dataset construction performed**

Manifest SHA-256:
`ca727489294c451987117466b2d80aa841b7d8c5bef9e96874dcf88aa40a80ce`.

## Scope and method

B1 selects the smallest defensible source set for a future Taiwan financial-text dataset. It does
not treat technical accessibility as permission, does not infer sentiment labels, and does not
merge official-announcement time with media-publication time.

The audit reused existing repository evidence for FSC, TWSE, FinMind, TWMD, TEJ/AP11,
`tw-finance-159M`, derived `tw-fsc` and eLAND. New network research was limited to reading public
official documentation for GDELT, TWSE/TPEx, Data E-Shop and three media candidates. No API/data
probe, protected-page access, corpus download, model call, manual label or training run occurred.

The complete field-level decision record is
`research/configs/b1_source_candidate_manifest.v1.json`; its Pydantic schema and guards are in
`research/planning/b1_source_audit.py`. The manifest, rather than this summary table, is the
machine-readable authority for approved and prohibited purposes.

## Decision summary

| Source | Type | B1 status | Approved B2 role / reason |
| --- | --- | --- | --- |
| FSC filtered 6,021-record corpus | Domain corpus | `ACCEPT_PRIMARY` | Taiwan financial-domain adaptation and representation only; never sentiment truth |
| TWSE daily material information OpenAPI | Official announcement | `ACCEPT_PRIMARY` | Listed-company title/explanation, ticker, clause, fact date and official publication time; forward/current daily coverage |
| TPEx daily material information OpenAPI | Official announcement | `ACCEPT_SECONDARY` | Same official-event role for OTC issuers; implement/schema-gate in B2 only if relevant |
| GDELT GKG/GAL | Media news | `ACCEPT_SECONDARY` | Historical media metadata, URL, volume/novelty and `MEDIA_TONE_PROXY`; no article-body mirror |
| FinMind `TaiwanStockNews` | Media news | `CONDITIONAL` | Deduplicated later-period title discovery only after an explicit B2 gate |
| MOPS interactive historical query | Official announcement | `HOLD` | Valuable fields, but no stable documented historical API/bulk-rights contract verified |
| TWSE Data E-Shop MOPS distribution | Licensed optional | `OPTIONAL_FUTURE` | Official contractual upgrade if future cost/terms/sample audit pass |
| TEJ/AP11 | Licensed optional | `OPTIONAL_FUTURE` | `OPTIONAL_HIGH_QUALITY_OFFICIAL_SOURCE`; no independent committed audit exists |
| TWMD major events | Licensed optional | `HOLD` | Existing entitlement probe returned HTTP 402 and zero usable rows |
| `tw-finance-159M` | Domain corpus | `HOLD` | Gated; underlying publisher rights, timestamp, duplicates and domain purity unresolved |
| derived `tw-fsc` | Domain corpus | `HOLD` | Gated OCR/VLM/HTML corpus; transformation and source-rights audit unresolved |
| Cnyes/Anue | Media news | `HOLD` | No documented public research API established; copyright notice forbids unapproved reuse |
| Yahoo Taiwan Finance | Media news | `HOLD` | No supported public news-ingestion API/right-to-corpus contract established |
| WantGoo | Media news | `HOLD` | Terms prohibit non-interface access and unapproved reproduction/use of text/data |
| eLAND | Historical rejection record | `HOLD` / permanently excluded | No calls, re-audit, labels, training, features or corpus merging |

Counts: two `ACCEPT_PRIMARY`, two `ACCEPT_SECONDARY`, one `CONDITIONAL`, two
`OPTIONAL_FUTURE`, eight `HOLD` and zero active `REJECT` entries.

## Accepted primary sources

### FSC filtered corpus

The five official archives and the 6,021-record family-isolated output already passed the
repository's checksummed source, structure, filtering and duplicate audits. Its final role is
**unlabelled Taiwan financial-domain language adaptation and representation learning**. It has no
general ticker key or validated polarity label, so it cannot become sentiment truth, event-time
truth or a substitute for labels. Special/third-party works and invalid/empty records remain
excluded under the existing [FSC open-data declaration](https://esg.fsc.gov.tw/SinglePage/Declare/).

### TWSE daily official announcements

The [TWSE OpenAPI catalogue](https://openapi.twse.com.tw/) documents
`/v1/opendata/t187ap04_L` as listed-company daily material information. The government-data record
identifies the fields and Government Open Data Licence v1. The repository's earlier anonymous
schema gate already observed the required fields without retaining response text.

For B2, `發言日期 + 發言時間` is the official publication-time candidate under an
`Asia/Taipei` parsing contract. `事實發生日` remains event metadata and must never replace the
publication time. The current daily endpoint is accepted for forward snapshots and available
daily records; it is not evidence of a complete historical archive.

## Accepted secondary sources

### TPEx daily official announcements

The government-data portal's [dataset 18418](https://data.gov.tw/dataset/18418) lists the same key
official fields—publication date/time, issuer code/name, title, clause, fact date and explanation—
for OTC issuers, updates daily, links an official OAS endpoint and states Government Open Data
Licence v1. It is complementary because the present ten-ticker research universe is listed-market
or ETF oriented and the repository has no TPEx provider yet. B2 may implement a bounded schema
gate, but must not treat OTC coverage as TWSE listed coverage.

### GDELT GKG/GAL

GDELT is accepted only as a secondary media layer:

- GKG 2.1 documents a record per processed document, source common name, source URL/identifier,
  extracted organizations, publication datetime and derived tone fields. Its publication field is
  distinct from the 15-minute GDELT batch time. [GKG 2.1 codebook](https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf)
- GDELT states its database is free/open and available as raw files or through BigQuery.
  [GDELT data access](https://www.gdeltproject.org/)
- The GAL backfile supplies standardized article metadata such as URL/title from 2020, while its
  own announcement warns of elevated duplicate URLs. [GAL documentation](https://blog.gdeltproject.org/announcing-the-gdelt-article-list-rss-feed/)
- The current translingual system includes Traditional and Simplified Chinese, but global
  monitoring is neither Taiwan-company complete nor finance-specific.
  [GDELT Translingual 2.0](https://blog.gdeltproject.org/gdelt-translingual-2-0-now-live-translates-everything-gdelt-monitors-in-109-languages-dialects/)

GDELT's `V1.5TONE` is dictionary/content-derived average media tone. It is **not validated Taiwan
financial sentiment**, human ground truth or P/N/N labels. Company association must use a frozen
ticker/company alias table plus extracted-organization evidence and must retain false-match and
miss flags. B2 may store GDELT metadata, hashes, URL and permitted title; it may not crawl or mirror
publisher bodies. Underlying article copyrights do not become open merely because GDELT metadata
is open.

## Conditional source

FinMind remains `CONDITIONAL`, not primary. The existing 280-request, ten-ticker 2018–2024 audit
found 1,547 rows, but all sampled 2018–2019 dates were empty, 2020 was sparse, descriptions were
absent, times were timezone-naive and semantically undocumented, exact-link duplication was
25.21%, and exact-title duplication was 20.49%. A later-period, deduplicated title/link discovery
role may be reconsidered by an explicit B2 gate. It cannot supply rich-text training, same-session
reaction alignment or sentiment truth.

## Optional future sources

- **TEJ/AP11:** retain the label `OPTIONAL_HIGH_QUALITY_OFFICIAL_SOURCE`. The project has user-side
  access notes but no independent committed field/licence/coverage audit. Future use requires an
  export sample, schema definitions, timestamp semantics, historical range, missingness/duplicate
  statistics and written storage/redistribution/public-output terms. Credentials must never be
  shared or committed.
- **TWSE Data E-Shop:** official contractual delivery can use email/API/URL, and the catalogue lists
  MOPS material-information products. It is not required for B2 and exact backfile, schema, price
  and internal/external-use rights must be audited after purchase, not assumed from the catalogue.
  [Data E-Shop](https://eshop.twse.com.tw/zh/home/index)

## HOLD and rejection boundary

### Historical MOPS UI

The interactive MOPS history query remains useful for human reference but lacks a verified stable
automation and reuse contract. B1 did not submit its undocumented forms. A documented official
feed or written permission is required before it can enter B2.

### TWMD, `tw-finance-159M`, derived `tw-fsc`

TWMD stays on HOLD: the existing three-period entitlement probe returned HTTP 402 and no records;
B1 did not troubleshoot billing. The two gated Hugging Face corpora also stay on HOLD because
their unresolved source-level rights, transformations, timestamps and duplication are not fixed by
a dataset-level card. The accepted FSC corpus makes further derived-corpus work unnecessary for
B2.

### Cnyes, Yahoo Taiwan Finance and WantGoo

No documented, supported public bulk-news API with adequate corpus rights was established for any
of these candidates. Cnyes explicitly reserves news/text/data rights in its
[copyright notice](https://www.cnyes.com/announce.htm). WantGoo's
[terms](https://www.wantgoo.com/terms-and-policies) require use through provided interfaces and
prohibit unapproved reproduction, distribution and other use. Yahoo content additionally mixes
partner rights. Technical frontend endpoints, if observable, are not an access or research licence.
All three therefore remain link-out candidates only; no scraping, body storage, training or
redistribution is approved.

### eLAND

eLAND remains `HOLD / EXCLUDED_FROM_ACTIVE_MODELING` and
`PERMANENTLY_EXCLUDED_FROM_ACTIVE_WORK`. B1 preserves only the existing
diagnostic history: mixed-domain public samples, non-financial contamination, abnormal/inconsistent
markup, unavailable full raw split, and unverified label distribution, duplicates, cross-split
leakage, provenance and financial-domain purity. No current API, replacement dataset or rescue
path was investigated.

## Frozen B2 whitelist and source architecture

Only these four source IDs are whitelisted:

1. `fsc_filtered_corpus` — core unlabelled domain text;
2. `twse_openapi_daily_material` — core listed-company official events;
3. `tpex_openapi_daily_material` — complementary OTC official events;
4. `gdelt_gkg_gal` — secondary historical media metadata and proxy signals.

Preferred B2 stack:

```text
FSC filtered corpus
  + TWSE/TPEx daily official announcements
  + bounded GDELT GKG/GAL media metadata
```

Fallback B2 stack if the bounded GDELT coverage/quality gate fails:

```text
FSC filtered corpus
  + TWSE/TPEx daily official announcements
```

The fallback documents limited historical media coverage instead of filling the gap through
fragile scraping. `CONDITIONAL`, `OPTIONAL_FUTURE`, `HOLD` and `REJECT` sources are not in the B2
whitelist. Adding one requires a new versioned audit decision, not an informal exception.

## B2 handoff constraints

B2 must keep `OFFICIAL_ANNOUNCEMENT` and `MEDIA_NEWS` as separate row types and preserve both
`source_timestamp` and its declared semantics. It must freeze a normalized schema, alias/ticker
mapping, availability cutoff, deterministic exact/near duplicate grouping, rights/retention tier,
source lineage, missingness and coverage report before B3 training.

B2's first external action should be a small, bounded GDELT Taiwan-company metadata probe with no
article-body fetch. It should answer coverage, company-match precision proxies, timestamp
availability, duplicates and source/outlet distribution. It must not use GDELT Tone as a label.
The official-source path should separately add a TPEx schema gate and snapshot TWSE/TPEx daily
records under their own timestamp contract.

## Completion statement

B1 passed. It performed documentation research but no API/data network probe and no bulk download.
No model was trained, no label or B2 row was created, no GAS/LINE behavior changed, and no deploy,
commit or push occurred. The next and only executable unit is **B2 — Taiwan Financial Text
Dataset**, which must wait for user approval.
