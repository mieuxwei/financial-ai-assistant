# Public Beta Demo GAS

This directory is the independent, public-safe GAS frontend layer for R1B. Create a **new** Apps
Script project and copy only these files. Never deploy them into the private project and never copy
the Desktop original or ignored migration source into the Demo project.

Required Script Properties (values must remain in Apps Script, never Git):

- `LINE_DEMO_CHANNEL_ACCESS_TOKEN`
- `DEMO_EDGE_GAS_SHARED_SECRET`
- `DEMO_FASTAPI_BASE_URL`
- `DEMO_GAS_SERVICE_TOKEN`

The Demo GAS URL is called only by the signature-verifying Security Edge. Although Apps Script Web
apps cannot reliably expose LINE's raw signature header, every accepted body must contain a fresh,
HMAC-signed edge envelope and an unused nonce. Portfolio truth is stored only by FastAPI.

The seven Flex builders cover main menu, mutation preview, portfolio list, portfolio health, stock
analysis, financial intelligence and limitations/settings. Add/update/delete all require an
explicit confirmation before the backend mutation.
