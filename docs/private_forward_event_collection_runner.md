# Private Forward Event Collection Runner

Status: **DEPLOYED / FIRST_BOUNDED_LIVE_SMOKE_VERIFIED**
Runner version: `b2-private-forward-event-runner-v1`

## Scope

This unit implements a local/private B2 forward collector for official TWSE and TPEx material
information. It does not deploy a scheduler, train a model, create sentiment labels, modify GAS or
LINE, or unlock current-market F11B-2 inference.

The existing application-news job remains unchanged. The dedicated entry point is:

```bash
python -m jobs.b2_forward --phase current
python -m jobs.b2_forward --phase evening
python -m jobs.b2_forward --phase next_morning
```

These commands perform real read-only provider requests and write private local evidence. They were
not executed during this implementation unit; tests use deterministic mock responses.

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

No scheduler is configured by this unit. A scheduler must use an Asia/Taipei-aware trigger and must
not infer exchange sessions from weekdays.

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

- `automatic_retraining = false`
- `scheduler_deployed = false`
- `raw_payload_public = false`

Forward collection is not sentiment ground truth, automatic model validation or automatic model
refresh.

## Remaining deployment gate

Before enabling a schedule, the project still requires explicit approval of:

1. a persistent private storage target;
2. one scheduler and its Asia/Taipei invocations;
3. sanitized failure monitoring;
4. a bounded private live-collection smoke test;
5. retention, disable and rollback controls.

The next unit is therefore:

`PRIVATE_FORWARD_EVENT_COLLECTION_DEPLOYMENT_CONFIGURATION`
