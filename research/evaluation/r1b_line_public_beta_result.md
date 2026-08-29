# R1B LINE Public Beta Sandbox Result

Date: 2026-08-30

Status: **LINE_PUBLIC_BETA_READY_FOR_MANUAL_SETUP**

Deployment: **NOT DEPLOYED**

## Decision

Repository implementation, security contracts, isolated persistence schema, public-safe Demo GAS,
tests and manual setup/rollback guidance are complete. A deployed success claim is not permitted
until a new Demo LINE OA, Demo Messaging API channel, Demo GAS project, Cloudflare Worker, FastAPI
service, managed PostgreSQL database and Demo-only secret stores are explicitly created and pass
bounded end-to-end verification.

## Implemented topology

```text
New Demo LINE OA
  → Cloudflare Worker raw-body security edge
  → independent public-safe Demo GAS frontend processing layer
  → existing FastAPI extended with /api/v1/demo
  → dedicated managed-PostgreSQL demo_* tables + controlled research fixture
  → Demo GAS Flex rendering
  → Demo LINE reply
```

Cloudflare Worker was selected over a second FastAPI edge to keep raw signature verification small,
separate and secret-minimal. The backend remains the application/data authority; GAS remains the
LINE routing, conversation, preview/confirmation and presentation authority.

## Security and identity

- LINE HMAC-SHA256 Base64 verification uses exact raw body bytes and timing-safe comparison.
- Missing, invalid and modified-body signatures fail before forwarding.
- Raw LINE user ID is transformed at the edge to `dp_ + HMAC-SHA256`; it is not forwarded or
  persisted.
- Edge-to-GAS envelopes are HMAC signed and enforce schema, five-minute age and nonce replay cache.
- GAS-to-FastAPI uses a dedicated bearer service token plus the derived principal.
- Holding mutation idempotency is transaction-backed with a unique principal/event constraint.
- Every holding lookup includes principal ownership; cross-user read/update/delete tests fail closed.
- No secret value, private resource ID or private GAS source is part of the release tree.

## Portfolio behavior

- Frozen 10-ticker universe is loaded from the authoritative Track A dataset config.
- Maximum five holdings per Demo principal.
- Positive finite shares/cost with centralized ceilings.
- Add/update/delete require GAS preview and explicit confirmation.
- Updates/deletes require optimistic holding version.
- Retention is 30 days from meaningful updates.
- Delete-my-data cascades holdings, preferences/idempotency and user-scoped audit records.
- Cleanup command exists; scheduler status is `READY_FOR_SCHEDULE_CONFIGURATION`.
- No current price or ROI is shown because no audited, unblocked current source is enabled.

## Research boundary

- Existing synthetic 2330 fixture is reused without model inference or provider calls.
- Other frozen tickers return `UNAVAILABLE_FOR_CONTROLLED_FIXTURE`, not fabricated scores.
- Current-market F7 remains disabled; F11B-2A remains 6/9 and 5/23.
- Chinese linguistic sentiment remains human-readable abstention with null output.
- Market reaction remains magnitude-only historical association; direction is null.
- Track A/B models and artifacts are unchanged.

## External state

- Demo LINE OA: pending.
- Demo GAS project: pending.
- Worker deployment: pending.
- Public-beta FastAPI hosting: pending.
- Managed PostgreSQL: pending.
- Webhook: not live.
- QR: `LINE_DEMO_QR_PENDING`.
- Private GAS/LINE/holdings: unchanged.
- R1A public web demo: unchanged and still deployed.

## Next unit

Complete `docs/line_public_beta_setup.md`, then run **R1B Deployment Verification**. Do not begin a
new research milestone or F11B-2.
