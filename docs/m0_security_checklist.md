# M0 External Security Checklist

Repository-side secret controls are implemented, but the following account-level actions require the project owner and cannot be proven from source code alone:

- [ ] Revoke and rotate the LINE channel access token found in the private GAS source.
- [ ] Revoke and rotate the Gemini API key found in the private GAS source.
- [ ] Revoke and rotate the Perplexity API key found in the private GAS source.
- [ ] Store replacement credentials only in an ignored `.env` or deployment Secret Manager.
- [ ] Review the source-backup Google Doc sharing permissions.
- [ ] Review or remove historical Google Doc versions that contain old source credentials.
- [ ] Review Apps Script deployments and installed triggers.
- [ ] Confirm the old GAS and Sheet remain private during migration.

Do not paste secret values, raw LINE user IDs, Google resource IDs, holdings, or screenshots into this checklist.
