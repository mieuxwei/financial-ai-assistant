# GAS Migration Safety Freeze — Internal Archive

> Retained to document the private-system safety boundary. Private paths and identifiers are
> intentionally abstracted; this file is not a deployment guide.

Status: **R0 backup verified; live behavior unchanged**  
Date: 2026-08-29

## Authorization boundary

The user authorizes future modification of the private GAS project only under this immutable
backup/rollback boundary. R0 itself authorizes no behavioral edit, deployment, webhook change,
trigger change, Sheet change or holdings mutation.

The existing LINE bot remains the product. Future Financial AI commands must be additive branches;
they must not replace or delete unrelated legacy functions.

## Private backup layout

All private source copies are Git-ignored under:

```text
.tools/private/gas-migration/r0-20260829/
├── immutable-original/
│   ├── code.gs
│   └── appsscript.json
└── migration-copy/
    ├── code.gs
    └── appsscript.json
```

- `immutable-original/*` permissions: read-only (`0400`).
- `migration-copy/*` permissions: owner read/write (`0600`).
- `.tools/` is excluded by `.gitignore`; do not force-add either tree.
- The original supplied private files were read after backup and remained byte-identical.

## Verification

R0 used both byte comparison and SHA-256:

| File | SHA-256 | Result |
| --- | --- | --- |
| `code.gs` | `a995a4c5ba83149e996a2d132b5e386b9d48b85269cf2fcd50b3a54c6828f8e2` | original = immutable = migration copy |
| `appsscript.json` | `4fadeff155b4ed58f5c257ccf221d1037a37b285e7f76d01b751a459839c9e22` | original = immutable = migration copy |

Do not edit `immutable-original`. All future code work begins from `migration-copy`, and a live GAS
change requires a separately reviewed deployment/rollback unit.

## Sanitized inventory

Located original inputs: two private legacy GAS source files outside the repository. Their local
absolute paths are intentionally omitted from this public archive.

Manifest facts:

- V8 runtime;
- `Asia/Taipei` timezone;
- deployment declares execute-as deploying user and anonymous web-app access;
- OAuth scopes include Apps Script project access, Docs, Drive, Sheets and external requests.

Script Property **names** observed (values deliberately not read into documentation):

- `LINE_USER_ID`;
- `LINE_ACCESS_TOKEN`;
- `PERPLEXITY_API_KEY`;
- `SPREADSHEET_ID`;
- `GEMINI_API_KEY`;
- `AUTH_USERS` and per-user `STAGE_*`;
- usage/balance/date counters and `LAST_INVENTORY_UPDATE`.

Private Google resource identifiers exist in the legacy source but are intentionally omitted here.
No credential or resource-identifier value belongs in public documentation or repository files.

## Preserved legacy behavior

- `doPost`, follow/text/image routing and temporary authorization state;
- Flex menus, portfolio/report/alert/help/quota cards and LINE reply/push;
- Gemini text/screenshot extraction with confirmation;
- Google Sheets holdings add/update/full synchronization;
- Yahoo `.TW`/`.TWO` price lookup, ROI and 5/20-session averages;
- stop-profit/stop-loss alerts;
- morning/afternoon report entry functions;
- Perplexity on-demand research/news with citations;
- provider counters/balance display and Sheet error logging.

## Trigger and deployment inventory status

The files prove that `morningPushReport` and `afternoonPushReport` entry functions exist. Installed
trigger schedules, trigger IDs, deployment IDs/URLs and last-run state are Apps Script account
state and were **not accessible from the supplied source files**. They remain `UNKNOWN / MUST
INVENTORY READ-ONLY BEFORE F11B-1 DEPLOYMENT`.

The existing project identity and private resource identifiers were not copied into this public
document. Before a deployment unit, record them only in private ignored inventory and never print
secret values.

## Required F11B rollback checklist

- hash immutable backup before and after work;
- diff migration copy against immutable source;
- verify legacy commands remain present;
- do not alter holdings, Sheet schema, screenshot writes or schedules in F11B-1;
- test new routes with controlled fixtures first;
- authenticate GAS-to-FastAPI requests and reject replay/expired requests;
- use bounded timeouts, safe errors, idempotency, identity mapping, rate limits and audit records;
- deploy only as a new recoverable version with the old version/URL available for rollback;
- verify morning/afternoon triggers after deployment without changing schedules unless separately
  authorized;
- never move ML/NLP or the 23-feature calculation into GAS.

## R0 conclusion

The immutable backup and migration copy exist and match the original byte-for-byte. No live GAS
source, webhook, deployment, trigger, Sheet or holdings behavior changed.
