# LINE Public Beta Manual Setup

Status: **LINE_PUBLIC_BETA_READY_FOR_MANUAL_SETUP**

Never paste credentials into chat, Git, source code, screenshots or documentation. Store each value
only in the destination secret store named below.

LINE requires HMAC-SHA256 over the exact, unmodified webhook body before JSON parsing. The setup
therefore follows LINE's [official verification procedure](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/)
and stores Worker values using [Cloudflare secrets](https://developers.cloudflare.com/workers/configuration/secrets/).

## Prerequisites

- A new Demo LINE Official Account and Messaging API channel, visibly named as a public beta.
- A new Apps Script project dedicated to the Demo.
- A Cloudflare account for the Worker edge.
- A personal Vercel Hobby account and a Neon account for the dedicated Free PostgreSQL project.
- The reviewed repository commit available to the chosen backend deployment.

## Checklist

### 1. Create the isolated LINE Demo resources

- [ ] Create a **new** LINE Official Account; do not reuse the private OA.
- [ ] Enable/link its Messaging API channel.
- [ ] Copy the Demo Channel Secret directly into the Cloudflare secret store as
      `LINE_DEMO_CHANNEL_SECRET`.
- [ ] Issue a Demo channel access token and store it only in the new Apps Script project's Script
      Properties as `LINE_DEMO_CHANNEL_ACCESS_TOKEN`.
- [ ] Keep the webhook disabled until the Worker URL and all downstream services pass checks.

### 2. Create independent random secrets

Generate three different values of at least 32 random bytes. Do not reuse LINE credentials.

- [ ] `DEMO_IDENTITY_SECRET`: Cloudflare Worker initially; when R1B-UX1 is enabled, the identical
      value is also stored in Vercel Production so LIFF and webhook traffic derive one principal.
- [ ] `DEMO_EDGE_GAS_SHARED_SECRET`: identical value in Worker secret store and Demo GAS Script
      Properties.
- [ ] `DEMO_GAS_SERVICE_TOKEN`: identical value in Demo GAS Script Properties and FastAPI secret
      environment.

### 3. Create the Neon Free sandbox database

- [ ] Create a new Neon project dedicated to `financial-ai-public-beta`; choose a region close to
      the Vercel Function region where available.
- [ ] Keep the project on the Free plan and enable scale-to-zero behavior.
- [ ] Copy the pooled PostgreSQL connection string directly into the Vercel environment setting
      as `DATABASE_URL`; keep `sslmode=require` and do not paste it into chat or Git.
- [ ] Do not point `DATABASE_URL` to a private or research database.

### 4. Deploy FastAPI to Vercel Hobby

- [ ] Use a personal Vercel Hobby account. The release is a personal, non-commercial portfolio
      project and must not be used commercially under Hobby.
- [ ] Import the reviewed GitHub repository as a new Vercel project. Do not import any private GAS
      repository or local ignored directory.
- [ ] Keep the repository root as the project root. Vercel reads the FastAPI entrypoint and build
      command from `pyproject.toml`.
- [ ] Keep the committed single Function region `sin1` so compute is close to the Neon Singapore
      database.
- [ ] Configure only `APP_ENV=production`, `DATABASE_URL` and `DEMO_GAS_SERVICE_TOKEN` for the
      Production environment. Do not expose them to Preview unless a separate preview database is
      intentionally created.
- [ ] Keep all provider/LINE/private credentials absent from the backend.
- [ ] The production build runs `scripts/vercel_build.py`, which fails closed without PostgreSQL and
      applies the Alembic migrations. Inspect the first build log and verify migration success.
- [ ] Verify the Vercel HTTPS `/health` endpoint.
- [ ] Verify an unauthenticated `/api/v1/demo/portfolio` request returns 401.
- [ ] Record the HTTPS base URL without embedding it in source.
- [ ] Keep the Vercel service URL out of public docs. Store it only as `DEMO_FASTAPI_BASE_URL`
      in Demo GAS Script Properties.
- [ ] Configure `financial-ai-demo-cleanup` only after a protected cleanup route or other safely
      authenticated scheduler path exists. Until then, record
      `READY_FOR_SCHEDULE_CONFIGURATION`; do not expose the cleanup command publicly.
- [ ] Monitor Hobby usage. If included limits are exhausted, accept service pause rather than
      enabling paid on-demand usage.

Vercel Hobby is free and does not have a billing cycle, but it is limited to personal,
non-commercial use. Both Vercel Functions and Neon may cold-start. One manual `/health` warm-up
before a scheduled demo is allowed; do not create keep-alive traffic.

### 5. Create and deploy the new Demo GAS project

- [ ] Create a blank Apps Script project whose name includes `Public Beta Demo`.
- [ ] Copy only the files in `line_adapter/public_beta/`; do not copy Desktop GAS or ignored private
      migration files.
- [ ] Add Script Properties:
  - `LINE_DEMO_CHANNEL_ACCESS_TOKEN`
  - `DEMO_EDGE_GAS_SHARED_SECRET`
  - `DEMO_FASTAPI_BASE_URL`
  - `DEMO_GAS_SERVICE_TOKEN`
- [ ] Confirm no Sheet ID, private user ID, provider key or private URL exists.
- [ ] Deploy as a new Web app executing as the owner and accessible to the Worker.
- [ ] Save the generated Demo web-app URL directly into Cloudflare as `DEMO_GAS_WEB_APP_URL`.

### 6. Deploy the Cloudflare Worker

- [ ] Deploy `security_edge/worker.mjs` using `security_edge/wrangler.toml`.
- [ ] Store these Worker secrets:
  - `LINE_DEMO_CHANNEL_SECRET`
  - `DEMO_IDENTITY_SECRET`
  - `DEMO_EDGE_GAS_SHARED_SECRET`
  - `DEMO_GAS_WEB_APP_URL`
- [ ] Confirm a POST without `X-Line-Signature` returns 401.
- [ ] Confirm logs do not contain raw request bodies or raw LINE user IDs.
- [ ] Copy the Worker HTTPS URL into the Demo LINE Messaging API webhook setting.

### 7. Enable and verify the webhook

- [ ] Use LINE's Verify function; it must succeed through Worker → Demo GAS.
- [ ] Enable webhook delivery only on the Demo channel.
- [ ] Add the Demo OA as a friend and verify the Public Beta main menu appears.
- [ ] Confirm the private LINE OA behavior is unchanged.

### 8. Functional and isolation smoke test

- [ ] User A accepts the disclosure and adds 2330 through preview → confirm.
- [ ] Re-send the same confirmed event in a controlled test and confirm no duplicate holding.
- [ ] User A views, updates and deletes the holding through confirmations.
- [ ] User A adds a holding and opens Portfolio Health; it must say controlled research signal and
      must not show current price/ROI.
- [ ] A non-2330 frozen ticker must show fixture unavailable, not an invented score.
- [ ] User B must see an empty independent portfolio and cannot access User A's holding ID.
- [ ] Financial Intelligence must show Chinese sentiment abstention and no direction.
- [ ] Delete My Demo Data, then verify portfolio and disclosure state are empty.
- [ ] Confirm screenshot import is marked unavailable.

### 9. QR / portfolio release

- [ ] Obtain the official Add Friend URL/QR from the new Demo LINE OA.
- [ ] Confirm it is not the private OA.
- [ ] Only then add the QR asset to the portfolio. Until then use `LINE_DEMO_QR_PENDING`.

## Rollback / disable

1. Disable the Demo LINE webhook.
2. Revoke the Demo channel access token.
3. Disable the Cloudflare Worker route/service.
4. Disable the Demo GAS web-app deployment.
5. Pause or remove the Vercel project.
6. Delete or securely purge the Demo sandbox database if required.
7. Verify the private OA and private GAS were not changed.

## R1B-UX1 — enable the LIFF multi-holding editor

Complete this only for the existing **Demo** provider/resources. Do not place secrets in chat.

1. In LINE Developers, create a LINE Login channel under the **same provider** as the Demo
   Messaging API channel. This is required so the verified LINE subject derives the same Demo
   principal as webhook traffic.
2. Add one LIFF app with endpoint URL
   `https://financial-ai-assistant-one.vercel.app/demo/liff/portfolio`, size `Tall` or `Full`, and
   scope `openid`. Do not request profile/email scopes because the editor does not need them.
3. In Vercel Production environment variables, set:
   - `LINE_DEMO_LIFF_ID` — public LIFF app ID;
   - `LINE_DEMO_LIFF_CHANNEL_ID` — expected LINE Login channel ID;
   - `DEMO_IDENTITY_SECRET` — exactly the existing Worker identity secret;
   - `DEMO_LIFF_SESSION_SECRET` — a new independent random secret of at least 32 bytes;
   - `DEMO_LIFF_SESSION_MINUTES=15`.
4. Redeploy Vercel and verify the page loads without exposing configuration secrets.
5. Create a replacement Demo rich menu whose 「新增持股」 area uses the URI action
   `https://liff.line.me/{LIFF_ID}`. Keep the current menu until the replacement passes smoke test;
   then set the replacement as default. Do not use the private OA menu.
6. In LINE, open the editor, confirm the existing sandbox holding appears, add at least two more
   rows, preview once and save. Reopen it and verify all rows remain.
7. Test stale-tab rejection, duplicate-ticker rejection, five-holding limit and user isolation.
8. Confirm the legacy text add flow still works as fallback and the private OA remains unchanged.

If any target resource cannot be positively identified as Demo, stop before changing it.

## Deployment verification handoff

After steps 1–7 are complete, provide only non-secret resource status to the release operator. Do
not provide tokens. The operator should then run bounded checks for webhook verification,
add/update/delete, portfolio health, two-user isolation, delete-my-data, QR identity and
private-environment non-impact.
