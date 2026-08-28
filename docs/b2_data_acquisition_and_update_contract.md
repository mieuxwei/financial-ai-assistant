# B2 Data Acquisition and Update Contract

Contract version: `b2-taiwan-financial-text-v1`  
Schema version: `b2-financial-document-v1`  
Frozen: 2026-08-29  
Status: **B2 COMPLETE / not deployed / B3 not started**

This is the single authoritative long-term acquisition contract for the Taiwan Financial Text
Dataset. The machine-readable authority is
`research/configs/b2_taiwan_financial_text.v1.json`. B1 source decisions remain authoritative and
this contract cannot activate a conditional, optional, HOLD or excluded source.

## Completion and waiting boundary

There is **no minimum forward-collection period**. The project does not wait 30 days, 90 days,
126 sessions or six months before B3, B4, B5, F11B or F12. TWSE/TPEx/GDELT accumulation is a
long-term enhancement and may support future longitudinal/external validation, not a completion
prerequisite.

B2 does not deploy collectors, create paid infrastructure, retrain models, create sentiment labels,
modify GAS/LINE, or start B3/F12.

## Frozen normalized document schema

Every normalized document version uses these fields:

- `schema_version`, `document_id`, `document_version_id`;
- `source_id`, `source_type`, `provider`, `external_id`;
- timezone-aware `publication_timestamp`, declared `timezone`, `timestamp_semantics` and
  `timestamp_precision`;
- timezone-aware `ingestion_timestamp`;
- `language`, optional `title`, `permitted_text`, `source_url`, `event_category`;
- zero or more `ticker_mappings` with company, deterministic method and confidence;
- `content_hash`, `raw_payload_ref`, `lineage`, `rights_tier` and
  `public_demo_text_allowed`;
- optional `media_tone_proxy`, valid only for `MEDIA_NEWS`.

`OFFICIAL_ANNOUNCEMENT`, `MEDIA_NEWS` and `DOMAIN_CORPUS` never collapse into one semantic type.
Official publication time, GDELT source-document publication time, GDELT batch time, FSC date-only
publication and local ingestion time remain separate facts.

### Identity and revision rules

- `document_id = sha256(source_id + stable provider identity)`.
- `document_version_id = sha256(document_id + content_hash)`.
- Identical retries produce the same IDs and are no-ops.
- Changed content for the same source identity creates a new immutable version; it never overwrites
  the prior version.
- Official identity uses source + ticker + official publication timestamp + normalized title when
  no provider ID exists.
- GDELT identity uses its document identifier or canonical source URL.
- Exact content/title/canonical-URL hashes are deterministic. Near-duplicate/syndication grouping
  is stored as an additional relationship and does not erase source lineage.
- One media document may map to several tickers. An official company code uses
  `official_company_code`; media aliases use an explicit alias method and confidence.

## Three storage layers

### RAW

Exact provider responses are retained only where B1 rights permit. A raw envelope records source,
endpoint/partition or query, fetch time, HTTP/source metadata, byte hash and run ID.

- Local research: ignored `.tools/` paths.
- Recommended deployment: private S3-compatible object storage under
  `raw/{source}/{yyyy}/{mm}/{dd}/{run_id}` with encryption, object versioning and lifecycle rules.
- GDELT raw means GDELT metadata only—never publisher article bodies.
- FSC reuses its already pinned private corpus and archive hashes; it is not recollected.

### NORMALIZED

Canonical B2 documents live in managed PostgreSQL in the recommended architecture. Private
versioned JSONL/Parquet snapshots and their manifests belong in private object storage. Local runs
use ignored `.tools/datasets/b2-taiwan-financial-text-v1/`.

### FEATURE / INTELLIGENCE

B3/B5 may later store embedding references, event categories, automated signal/impact outputs,
media-tone proxies and inference versions. These records reference `document_version_id`; they do
not modify RAW or NORMALIZED data. Daily collection never implies daily retraining.

The public Git repository contains code, schema, configs, tests, small synthetic fixtures,
aggregates, hashes and documentation only. It excludes corpora, private payloads, secrets,
restricted text, holdings and model artifacts.

## Source-specific collection contracts

### FSC — static domain corpus

- Method: reuse checksummed `fsc-domain-corpus-v1` only.
- Frequency: none; no scheduled collection.
- Time: publication date precision only, represented with explicit `Asia/Taipei` plus
  `timestamp_precision=date`; this is not an intraday event time.
- Raw/normalized: ignored private FSC corpus → private B2 snapshot.
- Dedup/identity: approved content hashes and family-isolated split; B2 identity derives from the
  FSC source record ID.
- Retention/rights: non-commercial domain adaptation/representation only; no public raw text,
  ticker invention, sentiment truth or automatic adoption of later archives.
- Update: a future corpus version requires a separate source audit, hashes and new dataset version.

### TWSE — official listed-company forward ingestion

- Method: documented `/v1/opendata/t187ap04_L` daily OpenAPI.
- Schedule: configurable `16:30`, `21:30`, and optional `08:00` next-day reconciliation,
  `Asia/Taipei`.
- Timestamp: `發言日期 + 發言時間` is official publication time; `事實發生日` is separate metadata.
- Retry: 20-second request timeout, three attempts, 1/2-second exponential backoff for timeout,
  transport failure, 429 and retryable 5xx. Non-retryable 4xx and schema failures stop the source.
- Late arrival/revision: evening and next-morning re-fetch; same version is a no-op and changed
  content is an immutable new version.
- Rights: Government Open Data Licence v1 fields only; general MOPS pages are outside the contract.
- Coverage: forward/current daily source. No multi-year historical completeness claim.

### TPEx — official OTC-company forward ingestion

TPEx follows the TWSE retry, reconciliation, identity, storage and official-time rules using the
official dataset 18418 CSV/API. B2 implemented the CSV provider and validated a bounded current
snapshot on 2026-08-29: all 65 logical CSV records parsed, all nine required columns were present,
and all publication datetimes were timezone-aware. The response was stored only under system
temporary storage and was not committed. TPEx remains complementary and does not create listed-
company coverage.

### GDELT — media metadata

- Method: bounded GKG/GAL partition or BigQuery metadata query; DOC API is permitted only for
  bounded recent discovery and is not a historical-backfill substitute.
- Schedule: daily `02:30 Asia/Taipei`; reconcile the prior UTC day on the next run.
- Timestamp: retain GKG source-document publication time, GDELT batch time and ingestion time
  separately. Do not infer publisher timezone.
- Identity/dedup: GDELT document ID or canonical URL, then exact title/content hash; preserve
  outlet, query/partition and many-to-many company mappings.
- Rights: source URL, source metadata, themes, organizations, event metadata and Tone may be stored.
  Publisher bodies may not be fetched, cached, trained on or redistributed.
- `Tone` is `MEDIA_TONE_PROXY`, never validated sentiment or P/N/N ground truth.
- Retry: 30-second timeout, three attempts, 2/4-second backoff; identical metadata retry is a no-op.

A bounded maximum-25-record DOC API probe was attempted during B2 without article-body access.
The official API presented an expired TLS certificate, so the request stopped; TLS verification
was not bypassed and zero records were accepted. Therefore the B2 v1 historical snapshot uses the
official-and-domain fallback stack. GDELT remains whitelisted for a future properly authenticated/
verified bounded metadata extraction, but has a zero-row baseline in this dataset version.

## Failure, recovery and alert policy

Each source is isolated within a run. Raw response persistence occurs before normalization where
rights allow, making parse failures reproducible without repeated network access.

- Timeout/429/retryable 5xx: bounded retry and exponential backoff.
- Non-retryable 4xx, TLS failure or schema mismatch: no bypass; mark source run failed.
- Row-level parse failure: retain raw snapshot privately, quarantine row identity/error code, write
  valid rows atomically, and record accepted/rejected counts. Do not silently coerce timestamps.
- Partial multi-source failure: successful sources commit independently; failure in one source does
  not roll back another.
- Next run: reconcile the prior source day/window and use immutable IDs to avoid duplicates.
- Logs: source/run ID, start/end, status, counts, retry count, hashes, schema version and error code;
  never payload text, URL credentials or secrets.
- Alert after: final retry exhaustion, TLS/certificate error, required-field/schema change,
  checksum conflict for an existing version, two consecutive missed scheduled windows, or unusual
  zero-row result relative to that source's established baseline.

## Recommended and fallback deployment

Recommended: **GitHub Actions scheduled Python jobs + managed PostgreSQL + private S3-compatible
object storage**. Jobs use environment-scoped secrets, least privilege, concurrency locking and
source-specific schedules. GitHub stores code/log-safe aggregates only. This is a design—not a
deployed workflow in B2.

Fallback: **private always-on Python host with cron/launchd + encrypted ignored storage + private
PostgreSQL/SQLite**. This preserves the same IDs/manifests but has weaker uptime and disaster
recovery, so it is a personal research fallback rather than public production architecture.

## Data update versus model refresh

Collection is scheduled; training is not. New records never overwrite a validated artifact. A
future refresh must:

1. create a new candidate and dataset/config version;
2. retain the previous production/research artifact;
3. rerun the frozen chronological validation protocol;
4. pass the frozen B4 decision criteria;
5. receive an explicit versioned promotion decision.

## B2 completion checklist

- B1 four-source whitelist preserved exactly;
- normalized schema and timezone/timestamp semantics frozen;
- stable identity, immutable revision and deterministic dedup rules implemented/tested;
- ticker/company mapping, rights, retention and public/private boundary defined;
- source lineage and dataset/config hashes recorded;
- 6,021-record historical FSC B2 snapshot constructed reproducibly;
- recurring TWSE/TPEx/GDELT contract and storage layers defined;
- retry, partial failure, reconciliation, logging and alert rules defined;
- model-refresh policy separated from data updates;
- no minimum future waiting period;
- no deployment, B3 training, GAS/LINE change, commit or push.

B2 is complete. The next executable unit is **B3 — Domain Adaptation & Candidate Signals**, which
requires separate user approval.
