# TWMD Pro Bounded Re-audit Result

Audit date: 2026-08-29  
Decision: **ACCEPT_SECONDARY**  
Boundary: **B3 not started; no bulk download, training, GAS change, Track A change, commit or push**

This post-B2 audit supersedes the earlier operational `HOLD` caused by HTTP 402, but it does not
rewrite the historical B1 manifest or the already-frozen B2 v1 snapshot. The accepted scope is
limited to TWMD's major-event taxonomy and issuer-mapping metadata. It does not accept every TWMD
dataset as usable.

## Method and credential safety

The audit used the ignored local `TWMD_API_KEY` through `X-API-Key`. The key, request header and
response text are absent from committed output. Eight endpoint/window probes were made; every call
requested at most two rows. Successful raw responses remain only in ignored
`.tools/datasets/twmd-pro-reaudit-v1/`; the public report contains schemas, counts and hashes only.

Config SHA-256:
`6c320dc4c5b0889333312dbd106e0c4027dabff95280ccdade2e19f836db1b5a`.

## Authentication and entitlement

Authentication is **confirmed** because the same key returned HTTP 200 from Pro-gated major-event
taxonomy calls. Endpoint-level results were:

| Dataset / endpoint | Small probe result | Returned fields / text boundary | Timestamp semantics | Decision for B2/B3 |
| --- | --- | --- | --- | --- |
| `GET /v2/datasets/major-event-taxonomy` | HTTP 200; two rows for 2330 in each of 2018 and 2024 | `ticker`, `market`, `event_date`, `event_time`, verbatim `subject`, inferred `event_class`, `confidence`, `rule_version`; no body | MOPS event publication date plus second-resolution clock field; response carries no timezone offset, so preserve the raw clock and treat `Asia/Taipei` as a source-contract assumption rather than an observed offset | **Accepted secondary** for event/title metadata; never sentiment truth |
| `GET /v2/datasets/company-news` | HTTP 200 but zero rows for 2018, 2024 and the documentation's 2026 sample date | Runtime declares metadata-only fields such as headline, summary, URL and source; no live row and no full body observed; `production_exposure=false`, `public_exposure=false` | Documentation advertises `published_at`, but no row was available to validate it | **HOLD** for historical news, rich text and B3 input |
| `GET /v1/filings/material-information` | HTTP 404 | No schema or row returned | Not testable | **HOLD**; documented legacy path is unavailable |
| `GET /v2/datasets/issuer-classification` | HTTP 200; two rows | `ticker`, `market`, taxonomy/version/class, provider/source role and `as_of_date`; no text | `as_of_date` is a current snapshot date, not an event/publication timestamp | **Accepted secondary helper only** for mapping/context |
| `GET /v2/datasets/news/mops-material-events` | HTTP 401 while other calls authenticated successfully | No row returned | Official documentation labels it private beta and metadata-only | **HOLD**; not entitled/private beta |

The live major-event calls establish that 2330 has retrievable records in both 2018 and 2024.
They do not prove completeness for every company or every date. TWMD's official dataset page reports
catalogue coverage from 1993-01-05 to 2026-08-27 and 1,025,009 rows; this audit did not bulk-download
or independently verify that catalogue-wide count.

## Contract discrepancy

The public major-event documentation currently illustrates `symbol`, `start_date` and `end_date`.
The live response contract instead exposes and applies `ticker`, `date_from` and `date_to`. Calls
using the documented names returned current unfiltered rows; corrected runtime names returned 2018
and 2024 rows. Any future connector must pin the observed runtime schema and fail closed if the
filter echo or returned dates leave the requested window.

## Licensing, storage and public-output boundary

TWMD's current terms grant a limited, non-exclusive, non-transferable and revocable right under the
active plan. They prohibit unauthorized resale, sublicensing and redistribution; dataset-specific
source licences and attribution continue to apply. The API key must not be shared, and plan scope,
quota and access can change. Therefore:

- raw samples remain private/ignored and are not committed or published;
- public artifacts may expose code, schema, counts, hashes, derived aggregates and attributed
  short official metadata only where the source licence permits;
- no bulk mirror, full-text republication or trial-account circumvention is approved;
- reproducibility depends on an active entitled plan, so TWMD cannot be the sole primary source.

Official references: [major-event taxonomy](https://twmarketdata.com/zh-TW/docs/api/companies-events/major-event-taxonomy),
[company news](https://twmarketdata.com/docs/api/news/company-news),
[private-beta MOPS events](https://twmarketdata.com/zh-TW/docs/api/preview/mops-material-events),
and [terms](https://twmarketdata.com/zh-TW/legal/terms).

## Final source decision

**ACCEPT_SECONDARY**

TWMD is useful as a licensed, structured secondary event-intelligence layer because authentication
works, 2018/2024 major-event rows are accessible, the event/title schema is compact, and ticker,
date, time, category, confidence and rule version are available. It is not primary because access
is plan-dependent, documented query names differ from the live contract, timezone is not encoded,
the taxonomy is inferred rather than official ground truth, company-news samples were empty, and
no full text was available.

B2 v1 remains immutable. The subsequent B2.1 amendment has now frozen the runtime query contract,
filter-window guard, timezone semantics, attribution/retention rules, deduplication and source
lineage. It did not construct a TWMD dataset, so B3 must still use only the existing B2 v1 snapshot
unless a separate bounded TWMD dataset build is approved. This audit itself did not begin B3.
