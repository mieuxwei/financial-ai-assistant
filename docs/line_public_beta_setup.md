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
- A Google Cloud project with billing enabled for Cloud Run and a Neon account for the dedicated
  Free PostgreSQL project.
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

- [ ] `DEMO_IDENTITY_SECRET`: Cloudflare Worker only.
- [ ] `DEMO_EDGE_GAS_SHARED_SECRET`: identical value in Worker secret store and Demo GAS Script
      Properties.
- [ ] `DEMO_GAS_SERVICE_TOKEN`: identical value in Demo GAS Script Properties and FastAPI secret
      environment.

### 3. Create the Neon Free sandbox database

- [ ] Create a new Neon project dedicated to `financial-ai-public-beta`; choose a region close to
      the Cloud Run region where available.
- [ ] Keep the project on the Free plan and enable scale-to-zero behavior.
- [ ] Copy the pooled PostgreSQL connection string directly into the Cloud Run secret/environment
      setting as `DATABASE_URL`; keep `sslmode=require` and do not paste it into chat or Git.
- [ ] Do not point `DATABASE_URL` to a private or research database.

### 4. Deploy the FastAPI container to Cloud Run

- [ ] Create a dedicated Google Cloud project or clearly isolated Demo service.
- [ ] Enable Cloud Run and Artifact Registry. Google requires a billing account even when usage
      remains inside its free allocation; create a small budget alert before deployment.
- [ ] Build from the repository `Dockerfile` using the reviewed commit.
- [ ] Select request-based billing, minimum instances `0`, maximum instances `1`, port `8080`, and
      a nearby region. Do not configure always-on CPU or a minimum instance.
- [ ] Allow unauthenticated HTTPS transport because Demo GAS is not a Google service identity;
      application access remains protected by the bearer service token.
- [ ] Configure only `APP_ENV=production`, `DATABASE_URL` and `DEMO_GAS_SERVICE_TOKEN`.
- [ ] Keep all provider/LINE/private credentials absent from the backend.
- [ ] The container runs `alembic upgrade head` before starting FastAPI; inspect the first startup
      log and verify migration success.
- [ ] Verify the Cloud Run HTTPS `/health` endpoint.
- [ ] Verify an unauthenticated `/api/v1/demo/portfolio` request returns 401.
- [ ] Record the HTTPS base URL without embedding it in source.
- [ ] Keep the Cloud Run service URL out of public docs. Store it only as `DEMO_FASTAPI_BASE_URL`
      in Demo GAS Script Properties.
- [ ] Configure `financial-ai-demo-cleanup` daily only if a free/safely bounded scheduler is
      available. Until done, record
      `READY_FOR_SCHEDULE_CONFIGURATION`.

Cost boundary: this topology has no intended fixed monthly service fee at small demo usage, but
Cloud Run/Google networking and Neon limits remain quotas, not a guarantee of a zero bill. Do not
create keep-alive traffic. Cloud Run and Neon cold starts are accepted; one manual `/health` warm-up
before a scheduled demo is allowed.

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
5. Stop the public-beta FastAPI service.
6. Delete or securely purge the Demo sandbox database if required.
7. Verify the private OA and private GAS were not changed.

## Return to Codex for deployment verification

After steps 1–6 are complete, provide only the non-secret resource status and open the Demo LINE
OA/hosting consoles if help is needed. Do not provide tokens. Codex should then run bounded checks
for webhook verification, add/update/delete, portfolio health, two-user isolation, delete-my-data,
QR identity and private-environment non-impact.
