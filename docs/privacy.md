# Privacy and Secret Handling

Do not commit credentials, identifiers, real portfolios, broker screenshots, import CSV files, or personal data. Local secrets belong only in ignored environment files; public research inputs must be example, synthetic, or anonymized data.

- Raw LINE user IDs must not be stored; account mapping uses a one-way hash.
- The local database, `imports/`, `uploads/`, `user_data/`, and private/raw data paths are Git-ignored.
- Request validation errors omit submitted values.
- Application logs must not include tokens, images, full holdings payloads, or LLM prompts containing private holdings.
- Portfolio ownership is enforced in every M2 route. Transitional `X-User-ID` is not sufficient for public authentication and must be replaced in M10.
- Broker screenshots are not supported or persisted in this iteration.
- Public demo data must use a physically separate demo portfolio/database environment.
