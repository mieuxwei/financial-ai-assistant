# Transitional LINE Adapter

The first-iteration backend contract for a single approved test user is:

```http
GET /users/{internal_user_id}/portfolio
X-User-ID: {internal_user_id}
```

This makes the M2 portfolio readable by a future transitional GAS adapter without copying legacy GAS code into this repository. The current GAS project has not been modified.

`X-User-ID` only enforces ownership in the development contract; it is not public authentication. Do not expose this route publicly or add a GAS caller until a trusted service-authentication mechanism is configured. M10 will move LINE webhook verification to Python and derive the user identity from the verified event.

Never place LINE tokens, raw LINE user IDs, Spreadsheet IDs, API keys, or private holdings in this directory.
