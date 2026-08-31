# Private Forward Event Collection Runner

Status: **DEPLOYED / FIRST_BOUNDED_LIVE_SMOKE_VERIFIED**
Runner version: `b2-private-forward-event-runner-v1`

## Scope

This component implements the private B2 forward collector for official TWSE and TPEx material
information. Deployment adds only scheduling and private archive persistence; it does not train a
model, create sentiment labels, modify GAS or LINE, or unlock current-market inference.

The existing application-news job remains unchanged. The dedicated entry point is:

```bash
python -m jobs.b2_forward --phase current
python -m jobs.b2_forward --phase evening
python -m jobs.b2_forward --phase next_morning
```

These commands perform real read-only provider requests and write private evidence. Automated tests
use deterministic mock responses; the separately documented deployment smoke test used one bounded
live collection.

## Frozen collection flow

```text
single-run lock
  -> official provider request with 1/2-second retry backoff
  -> persist byte-exact raw response in ignored private storage
  -> parse and normalize under the B2 schema
  -> persist immutable document versions
  -> persist hashed source/run manifest
  -> release lock
```

The default root is `.tools/private/b2-forward-events-v1`, which is Git-ignored. Raw payloads,
normalized explanations and manifests must remain private. Public Git may contain only code,
contracts, tests, aggregate decisions and hashes.

## Reconciliation contract

| phase | frozen schedule | purpose |
|---|---|---|
| `current` | 16:30 Asia/Taipei | first post-session official feed snapshot |
| `evening` | 21:30 Asia/Taipei | capture late same-day announcements or revisions |
| `next_morning` | 08:00+1d Asia/Taipei | final pre-session reconciliation |

The deployed GitHub Actions workflow runs these phases at the equivalent UTC times and also supports
manual dispatch. Scheduled execution can be delayed by the platform and must not infer exchange
sessions from weekdays.

## Idempotency and failure behavior

- A run ID is derived from runner version, phase and timezone-aware observation timestamp.
- Replaying the same run ID returns its verified immutable manifest without another provider call.
- Identical raw payloads and document versions are immutable no-ops across different runs.
- One-source failure produces `PARTIAL_OR_FAILED`, writes a sanitized manifest and raises a
  non-success result.
- Raw bytes are stored before parsing, so schema drift retains private diagnostic evidence.
- Error messages and raw responses are never printed by the CLI.
- A local atomic lock blocks overlapping runner processes.

## Lineage

Every successful source result records endpoint, content type, row count, raw SHA-256, aggregate
document-version SHA-256, publication range, timezone, retry contract and B2/runner versions. The
overall manifest has its own SHA-256 and explicitly records:

- `scheduler_deployed = true`
- `automatic_retraining = false`
- `raw_payload_public = false`

Forward collection is not sentiment ground truth, automatic model validation or automatic model
refresh.

## Deployment status

GitHub Actions, the private Cloudflare R2 archive, all three reconciliation schedules, manual
dispatch and same-run remote idempotency have been smoke verified. Operational details, cost
boundary, retention and rollback are recorded in `docs/forward_collection_deployment.md`.
