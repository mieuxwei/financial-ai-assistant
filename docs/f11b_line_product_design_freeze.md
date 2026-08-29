# F11B-D0 LINE Product, Multi-user and GAS/FastAPI Design Freeze

Status: **COMPLETE / DESIGN FROZEN / NO IMPLEMENTATION**  
Version: `f11b-line-integration-design-v1`  
Date: 2026-08-29

## Scope and non-goals

This milestone freezes product UX, identity, isolation, ownership, routing and migration gates. It
does not modify the Desktop original, private migration copy, live Apps Script, webhook, trigger,
Sheet schema, holdings, report schedules, secrets, Track A, Track B models or deployment. F11B-1A,
portfolio-write migration and live/current inference are explicit non-goals.

## Final LINE main menu

The menu has exactly six entries, in this order:

1. 📊 股票分析
2. 💼 持股健檢
3. 📰 金融情報
4. 📷 匯入持股
5. 🔎 新聞研究
6. ⚙️ 設定

晨報、收盤報、中文情緒、方向預測、BERT/GDELT/model SHA、quota/provider balance、debug and
developer status are not menu entries. Morning/closing reports live only under Settings. Technical
machine states are translated into human copy and never presented as product features.

## Frozen Flex layouts

### 股票分析 — any queryable stock

Field order: stock name/ticker → Track A communication band → historical percentile → relative-
volatility explanation → current price → daily change → MA5 → MA20 → recent event summary →
market-reaction magnitude → research limitations → Financial Intelligence/News Research buttons.

It never requires ownership and never shows up/down probability, return forecast, buy/sell advice
or guaranteed volatility. LOW/MODERATE/HIGH/VERY_HIGH is relative volatility-surprise
communication, not direction.

### 持股健檢 — only the authenticated user's holdings

Field order: stock name/ticker → holding quantity → average cost → current price → unrealized ROI
→ Track A band → historical percentile → recent event → market-reaction magnitude → MA5 → MA20 →
legacy price/risk reminder → non-investment disclaimer → Financial Intelligence/News Research
buttons.

This is an integration of private holdings, Track A, Track B and market information, not another
model. It is intentionally distinct from 股票分析 through cost, quantity and ROI.

### 金融情報 — Track B presentation

Field order: stock name/ticker → recent financial event → inferred `event_class` → event timestamp
→ source → market-reaction magnitude → historical percentile when a cutoff-safe stored B5 signal
exists → human-readable maturity/limitations.

The normal card does not print `ABSTAIN` or `AUTOMATED_SIGNAL_ONLY`. It says 「研究型自動訊號」
when necessary and 「目前不提供可靠的上漲／下跌方向預測。」 Chinese sentiment is omitted from
the normal card; a research-info view may say 「中文文字情緒目前尚未通過獨立驗證。」

Market-reaction bands mean the relative historical magnitude associated with similar event/context
features. They do not mean an event causes a return, predicts a percentage return or guarantees a
reaction.

## Import holdings target UX

Frozen future flow:

```text
broker screenshot → OCR/AI parse → structured preview → explicit user confirmation
→ one-time confirmation token → transactional portfolio write → result
```

Parse-then-write and replayable `EXECUTE|...`/`SYNC|...` are prohibited as the long-term design.
F11B-D0 does not implement the redesign. Screenshot minimization, provider disclosure, short
retention, user consent, idempotency and audit are mandatory before portfolio-write migration.

## News research UX

Legacy Perplexity research remains a product capability, later reframed as recent material news,
event organization, positive factors, risk factors, sources and citations. Prompts must eventually
remove buy/sell, target-price, explicit action and guaranteed-outcome language. D0 does not edit or
execute the live prompt.

## Settings and reports

Settings contains Notifications, Account, Help and an ADMIN-only management section. Each internal
user owns independent `morning_report_enabled` and `closing_report_enabled` booleans. No global
switch is allowed.

Morning reports may combine market context, the user's holdings, high Track A volatility attention,
Track B events, reaction magnitude, news and observation points. Closing reports may combine TAIEX,
portfolio performance, high-volatility names, events/reactions and next-session attention. 「觀察」
and 「需留意」 mean risk/event attention only, never buy/sell.

## Roles and authorization

- `UNREGISTERED`: welcome, onboarding and public-safe help only; no portfolio, preferences,
  reports or private history.
- `REGISTERED`: six product functions, personal settings and personal morning/closing reports.
- `ADMIN`: registered capabilities plus system status, error summaries, provider/quota admin and
  maintenance. These are never visible to ordinary users.

Authorization is checked in FastAPI for every user-scoped operation; menu visibility is not an
authorization control.

## Identity and authentication trust boundary

Final flow:

```text
LINE → raw-body/header-capable LINE signature verification edge
→ verified LINE subject → authenticated internal request
→ FastAPI identity mapping → internal user UUID → authorization → user-scoped data
```

LINE `userId` is an external identity attribute, not a public backend bearer token. Store only the
minimum mapping, preferably encrypted or keyed-HMAC indexed, and never log raw identifiers.

F10 `X-User-ID` is development-only and untrusted. The legacy allowlist is a transition safety
layer; a shared challenge is not public authentication. Apps Script web-app `doPost(e)` does not
reliably expose the `X-Line-Signature` request header required to verify the raw LINE body. Therefore
production webhook traffic must terminate at a component that can access raw body and headers
(for example FastAPI behind a suitable HTTPS edge) or pass through such a verifier before GAS.
Allowlist checks must never be relabeled signature verification.

For verified internal GAS-to-FastAPI calls, freeze `HMAC_SERVICE_REQUEST_V1`: key ID, timestamp,
nonce, method, path and body SHA-256 are signed. FastAPI verifies signature, clock skew, nonce
replay, route scope, rate limit and audit record. A GAS-asserted LINE ID is not trusted unless the
upstream LINE event authenticity has already been verified.

## User data isolation matrix

| Data type | Owner | Storage target | Isolation key | Readable by | Writable by | Audit required? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Portfolio | User | FastAPI database | internal user UUID | owner; scoped admin support | transactional portfolio service | Yes | No global Sheet portfolio in final design |
| Preferences | User | FastAPI database | internal user UUID | owner | preferences service | Yes | Versioned defaults |
| Morning report setting | User | FastAPI database | internal user UUID | owner/scheduler | settings endpoint | Yes | Independent boolean |
| Closing report setting | User | FastAPI database | internal user UUID | owner/scheduler | settings endpoint | Yes | Independent boolean |
| Temporary state | User/session | Expiring backend store | user UUID + state ID | owner workflow | state service | Yes | TTL; never global Script Property |
| Confirmation transaction | User | Transaction store | user UUID + one-time token | owner | confirm service once | Yes | Replay protected and idempotent |
| News history, if retained | User | Backend database | internal user UUID | owner | research service | Yes | Minimize/expire; public research may be shared separately |
| Audit logs | System/user-linked | Append-only audit store | actor UUID + event ID | authorized admin/privacy process | audit subsystem | Yes | Redact identifiers and secrets |
| Usage counters | User/system | Backend metrics store | user UUID + period | owner summary; admin aggregate | quota service | Yes | Ordinary users cannot see provider balance |

Every repository query must include the authorized internal user UUID. Database constraints and
service tests must prevent cross-user reads/writes. Global portfolio, notification switch and
temporary state are prohibited.

## GAS and FastAPI responsibilities

GAS remains a thin transition adapter: LINE entry or verified internal adapter, reply token,
minimal routing, Flex rendering, scheduled push entry points, necessary credentials and legacy
compatibility. It must not own AI inference, 23-feature engineering, BERT/NLP orchestration, market
pipelines, portfolio rules, transaction/idempotency logic, full authentication, complex storage,
retry orchestration or lineage.

FastAPI owns identity mapping, authorization, preferences, portfolio rules, preview/confirm,
idempotency, transactions, persistence, ingestion, Track A/Track B, features, scheduling policy,
retries, quotas, observability, audit, privacy, versioned contracts and abstention.

## Legacy feature preservation matrix

| Legacy capability | Current implementation | Future owner | LINE visibility | Migration stage | Must preserve? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Portfolio | GAS + Google Sheets | FastAPI portfolio service | 持股健檢 | Future write migration | Yes | User-scoped, transactional |
| Holdings import | GAS confirmation flow | FastAPI workflow | 匯入持股 | After read-only/current stages | Yes | Preview/one-time confirm |
| Screenshot parser | Gemini from GAS | Backend privacy-controlled OCR adapter | 匯入持股 | Future write migration | Yes | Consent/retention controls |
| Yahoo price | GAS Yahoo fetch | Audited market adapter | Analysis/check cards | F11B-2 or replacement | Yes | Must pass source gate |
| ROI | GAS calculation | FastAPI portfolio service | 持股健檢 | Portfolio migration | Yes | Cost/price user scoped |
| MA5 | GAS calculation | FastAPI market service | Analysis/check | F11B-2 | Yes | Cutoff parity required |
| MA20 | GAS calculation | FastAPI market service | Analysis/check | F11B-2 | Yes | Cutoff parity required |
| Alerts | GAS/Sheet rules | FastAPI scheduler/rules | Push/settings | Later migration | Yes | Not trading advice |
| Morning report | GAS trigger entry | FastAPI content/schedule; GAS push adapter | Settings only | Later migration | Yes | Per-user switch |
| Closing report | GAS trigger entry | FastAPI content/schedule; GAS push adapter | Settings only | Later migration | Yes | Per-user switch |
| Perplexity news | GAS prompt/API | Backend on-demand research adapter | 新聞研究 | Later prompt migration | Yes | Citations; remove trading actions |
| Flex menu | GAS renderer | GAS renderer fed by backend contract | Six-entry menu | F11B-1A | Yes | Buttons primary; commands fallback |
| Quota | GAS counters/card | FastAPI quota/observability | ADMIN only | Later migration | Yes internally | Hidden from ordinary users |
| Help | GAS card | GAS/FastAPI safe copy | Settings/help | F11B-1A | Yes | Research limitations |
| Error logging | Sheet logging | Backend structured observability | ADMIN summary only | Later migration | Yes | No secret/private payload logs |

Follow/text/image routing, LINE reply/push, holdings, screenshot import, price/change/ROI, averages,
alerts, reports, research, Flex and usage/error infrastructure remain product capabilities even
when ownership moves. Refactoring never means silent deletion.

## F11B-1A routing freeze

Buttons/Flex actions are primary; commands are fallback/testing/power-user routes:

| Route | UI action | Access | D0 behavior |
| --- | --- | --- | --- |
| `risk <ticker>` | 股票分析 | REGISTERED | Specification only |
| `intel <ticker>` | 金融情報 | REGISTERED | Specification only |
| `portfolio` | Portfolio overview | REGISTERED | Specification only |
| `portfolio-check` | 持股健檢 | REGISTERED | Specification only |
| `import-holdings` | 匯入持股 | REGISTERED | Specification only |
| `news <ticker>` | 新聞研究 | REGISTERED | Specification only |
| `settings` | 設定 | REGISTERED | Specification only |

Unregistered routing exposes only onboarding/welcome/help. Admin routes are separate, undisclosed
in the ordinary menu and backend-authorized.

## F11B-1B controlled demo

```text
LINE → GAS migration-copy → authenticated FastAPI request
→ deterministic fixture or validated stored artifact
→ GAS Flex renderer → LINE
```

Every card says `CONTROLLED RESEARCH DEMO`; it must not look live or prospective. The demo is
read-only, performs no portfolio write/provider/model inference and is rollback-tested against the
immutable GAS backup.

## F11B-2 current-market gate

F11B-2 is blocked until all nine checks pass: audited current OHLCV, audited TAIEX, exact 23-feature
parity, cutoff semantics, timezone, frozen missing-data rules, training/inference feature parity,
lineage and validation. The gate cannot be bypassed. D0 neither audits nor resolves these items.

## Security and privacy risks

Frozen findings: LINE signature is currently unverified; anonymous web-app exposure exists;
allowlist/shared challenge is insufficient; holdings writes are replay-sensitive; there is no
idempotency or transaction; clear-and-rebuild can lose/corrupt data; resource IDs are hard-coded;
holdings/screenshots are sent to external AI; the legacy Perplexity prompt conflicts with the
non-advice boundary; GAS is highly coupled. The legacy prototype is not production-secure.

Additional controls required before live use: signature edge, service HMAC and replay cache,
least-privilege secrets, internal UUID authorization, row isolation, one-time confirmation,
transactional writes, data minimization/retention, provider disclosure, redacted audit logs,
rate limits, safe errors, timeout/retry policies and incident/rollback procedures.

## Migration and rollback order

Order is D0 design → F11B-1A migration-copy routing → F11B-1B controlled read-only demo → F11B-2
only after its gate → future portfolio-write migration. Portfolio writes are deliberately last.

Immutable original remains read-only. Only the private ignored migration copy may change in a
separately approved implementation unit. Before any live deployment: hash backup, diff migration
copy, prove legacy routes, test controlled fixtures, create a recoverable new version, retain the
old deployment/URL and verify existing triggers without changing schedules. D0 changes none of it.

## Next boundary

The next and only executable unit is **F11B-1A — Controlled LINE Routing in Migration Copy**. It
requires separate approval and must not begin automatically.
