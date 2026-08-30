# Forward Collection Deployment

Status: **FORWARD_COLLECTION_READY_FOR_MANUAL_DEPLOYMENT**

Date: 2026-08-30
Automatic retraining: **false**

## Architecture decision

```text
GitHub Actions schedule / workflow_dispatch
  -> frozen TWSE + TPEx B2 runner
  -> ephemeral private working directory
  -> Cloudflare R2 Standard private bucket
       source/date/run raw bytes
       immutable normalized versions
       source manifests
       hashed overall run manifest
```

Cloudflare R2 Standard is selected because the runner produces small immutable binary/JSON objects,
R2 supports the S3 API and conditional `If-None-Match` writes, and its Standard free tier is
appropriate for three low-volume daily runs. Raw bytes are not placed in Neon/PostgreSQL or GitHub
Actions artifacts.

The R2 subscription and bucket do not yet exist. The repository implementation is complete, but
the workflow is not on the default branch and no live collection has run.

## Cost boundary

As of 2026-08-30, Cloudflare documents the R2 **Standard** monthly included usage as 10 GB-month of
storage, 1 million Class A operations, 10 million Class B operations and free R2 egress. Usage over
those allowances is billed; Infrequent Access does not receive the same free tier. The Cloudflare
account activation page currently shows $0 fixed monthly amount but requires a usage-based R2
subscription backed by the existing payment method. This project must not select Infrequent Access,
R2 SQL, Data Catalog, Pipelines or a paid Workers plan.

The GitHub repository is public. GitHub documents standard GitHub-hosted Actions as free for public
repositories. No Actions artifact or cache is used by this collector. Scheduled work may be delayed
or, under high load, dropped; the configured clock time is not a guaranteed execution second.

Neither provider promises permanent pricing. Operators must keep the bucket on Standard, monitor
usage and stop before any paid upgrade or unexpected usage growth.

References:

- <https://developers.cloudflare.com/r2/pricing/>
- <https://developers.cloudflare.com/r2/api/s3/api/>
- <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
- <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>

## Scheduler

The prepared workflow is `.github/workflows/forward-event-collection.yml`.

| phase | Asia/Taipei | UTC cron |
|---|---:|---:|
| `next_morning` | 08:00 | `0 0 * * *` |
| `current` | 16:30 | `30 8 * * *` |
| `evening` | 21:30 | `30 13 * * *` |

It also provides `workflow_dispatch` with a required phase and optional Asia/Taipei collection date.
One global concurrency group serializes runs. A ten-minute timeout prevents a stuck request from
occupying a runner indefinitely.

GitHub scheduled workflows run only when the workflow exists on the default branch. Therefore the
three triggers are **prepared but not enabled** until an authorized checkpoint is pushed.

## Private storage and object layout

Bucket requirements:

- Cloudflare R2 **Standard** storage class;
- private by default;
- `r2.dev` public development URL disabled;
- no custom public domain;
- no public listing or public access policy;
- scoped object read/write credentials for this bucket only.

Object layout:

```text
forward-events/
  source=twse/date=YYYY-MM-DD/run=<run-id>/
    raw/<raw-sha256>.bin
    normalized/<document-version-id>.json
    manifest/source.json
  source=tpex/date=YYYY-MM-DD/run=<run-id>/
    raw/<raw-sha256>.bin
    normalized/<document-version-id>.json
    manifest/source.json
  runs/date=YYYY-MM-DD/phase=<phase>/run=<run-id>/manifest.json
```

Every write uses `If-None-Match: *`. Existing identical bytes are accepted as immutable no-ops;
different bytes at the same key fail. The overall manifest is uploaded last and serves as the
remote completion marker.

## Lock and idempotency

- Local runner lock protects one process workspace.
- GitHub Actions concurrency serializes all scheduled/manual collection jobs.
- Before provider access, the R2 wrapper reads the deterministic remote manifest key.
- If the manifest exists and its SHA-256 verifies, the prior result is returned without constructing
  the provider runner or issuing a provider request.
- Conditional R2 object writes prevent double object creation if an unusual collision occurs.

This contract is automated in tests. Live same-run idempotency remains unverified until the first
manual workflow dispatch is repeated with the same phase and date.

## Secrets and repository variable

GitHub Actions secrets—values must never be copied into source, docs or logs:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT`

Repository variable:

- `R2_BUCKET_PRIVATE_CONFIRMED=true`, set only after dashboard verification that public access and
  custom domains are disabled.

`R2_PREFIX=forward-events` is non-secret and frozen in the workflow. The CLI prints only run ID,
phase, status, source count, manifest SHA and idempotency status.

## Failure and monitoring

`PARTIAL_OR_FAILED` is non-success and exits the workflow as failed. Schema drift keeps private raw
evidence but does not fabricate normalized success. Logs contain exception classes/safe summaries,
not raw payloads, credentials or full provider responses.

Monitoring uses native GitHub Actions status and account email notifications only. Operators should
enable failed-workflow email notifications and inspect the workflow summary; no PagerDuty, Sentry,
Slack or paid alerting service is introduced.

## Retention

Successful raw bytes, normalized versions, schema-drift evidence, manifests and hashes are retained
long term. Ephemeral runner directories and transient caches are discarded after upload. No
authoritative raw object lifecycle deletion is configured.

## First bounded live smoke test

After bucket and secrets exist and the workflow is pushed:

1. manually dispatch one applicable phase for the current Asia/Taipei date;
2. confirm TWSE and TPEx source statuses;
3. confirm private raw, normalized versions and source/overall manifests exist;
4. compare raw/document/manifest SHA lineage;
5. verify no public bucket URL or listing exists;
6. dispatch the exact same phase/date again;
7. confirm `reused_remote_manifest=true` and no new source request/object;
8. confirm no training/model job was triggered.

No historical backfill or second distinct run is required.

## Rollback

1. disable the GitHub Actions workflow or remove its schedules;
2. leave existing immutable R2 evidence intact;
3. revoke the scoped R2 access key if compromise or shutdown is suspected;
4. do not delete the historical bucket objects during ordinary rollback;
5. no model rollback is required because the collector never trains or promotes models.

## Health checks

Seven days after enablement, inspect scheduled-run count, success rate, last success, TWSE/TPEx row
counts, duplicates, schema drift, object count and manifest consistency. Do not wait seven days to
finish deployment verification.

After 30 days, run a Forward Dataset Health Audit covering temporal coverage, missingness, source
failures, duplicate rate, schema stability, source distribution and storage growth. Do not retrain.

After approximately 3–6 months of naturally future data, a separately approved Future External
Validation may compare frozen v1.0 against unseen observations. Collection never implies
`v1.0 -> retrain`; a new candidate and frozen evaluation milestone would still require approval.
