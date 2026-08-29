# F11B-1B Controlled Read-only LINE Demo

Status: **COMPLETE / NOT DEPLOYED**  
Contract: `f11b-controlled-line-demo-v1`  
Date: 2026-08-29

## Scope

F11B-1B connects only the private GAS migration copy's `risk <ticker>` and `intel <ticker>` routes
to a dedicated FastAPI endpoint backed by the pre-existing deterministic F11 synthetic fixture.
Every returned card says `CONTROLLED RESEARCH DEMO`. This milestone does not read current market
data, call a provider/model/LLM, read or write a portfolio, modify the live webhook, deploy, or begin
F11B-2.

```text
LINE test event → private GAS migration copy → HMAC-authenticated FastAPI endpoint
→ validated static fixture → GAS Flex renderer → controlled LINE payload
```

The implementation is locally and deterministically tested. Because neither GAS nor FastAPI was
deployed, no claim is made that a live LINE webhook currently reaches this endpoint.

## Supported controlled views

- `risk 2330` → synthetic stock-analysis Flex card;
- `intel 2330` → synthetic financial-intelligence Flex card.

The two menu labels without a ticker return safe instructions. `news <ticker>` and Settings remain
placeholders. Portfolio, holdings import, news and other legacy routes continue through their
existing compatibility paths. Only the designated synthetic ticker `2330` is accepted; another
ticker fails closed instead of receiving invented data.

Current price, daily change, MA5, MA20 and B5 stored reaction magnitude are absent from the frozen
fixture, so the cards explicitly mark them unavailable. They are not synthesized. The static risk
score is controlled interface data generated before this milestone and is not a live observation,
prospective evaluation or inference performed during an API request.

## Service authentication

The request uses `HMAC_SERVICE_REQUEST_V1` over:

```text
key_id\ntimestamp\nnonce\nmethod\npath\nbody_sha256
```

FastAPI verifies the configured key ID, ±300-second clock window, body SHA-256, constant-time HMAC
comparison and one-time nonce. Missing/tampered/replayed requests return `401`. Secrets are supplied
only through environment variables and GAS Script Properties; no value is committed. This service
authentication does not solve the frozen production LINE-signature limitation. A raw-body/header-
capable LINE verification edge remains mandatory before production use.

## Response boundary

The versioned response asserts:

- `fixture_only = true`;
- `read_only = true`;
- `live_market_data = false`;
- `external_api_called = false`;
- `model_inference_performed = false`;
- `portfolio_read = false`;
- `portfolio_write = false`.

GAS validates these fields, contract version, fixture ID, view and ticker before rendering. Any
drift produces a safe text error and does not fall back to live data.

## Rollback and next gate

Rollback is deletion/reversion of the additive 1B functions in the ignored migration copy plus the
dedicated controlled endpoint. Desktop original GAS, immutable backup and `appsscript.json` remain
unchanged. The later bounded gate audit passed only two of nine current-market gates, so F11B-2
integration remains blocked. See `research/evaluation/f11b_current_market_gate_audit.md`.
