# Transitional LINE Adapter

The first-iteration backend contract for a single approved test user is:

```http
GET /users/{internal_user_id}/portfolio
X-User-ID: {internal_user_id}
```

This makes the M2 portfolio readable by a future transitional GAS adapter without copying legacy
GAS code into this repository. F11B is pending; R0 created only a private ignored immutable backup
and migration copy, without changing live GAS behavior.

`X-User-ID` only enforces ownership in the development contract; it is not public authentication.
Do not expose this route publicly or add a GAS caller until F11B implements service authentication,
replay protection, timeout/error handling, identity mapping, rate limiting and audit logging.

Never place LINE tokens, raw LINE user IDs, Spreadsheet IDs, API keys, or private holdings in this directory.
