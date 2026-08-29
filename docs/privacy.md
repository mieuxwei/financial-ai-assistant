# Privacy and Secret Handling

Do not commit credentials, identifiers, real portfolios, broker screenshots, import CSV files, or personal data. Local secrets belong only in ignored environment files; public research inputs must be example, synthetic, or anonymized data.

- Raw LINE user IDs must not be stored; account mapping uses a one-way hash.
- The local database, `imports/`, `uploads/`, `user_data/`, and private/raw data paths are Git-ignored.
- Request validation errors omit submitted values.
- Application logs must not include tokens, images, full holdings payloads, or LLM prompts containing private holdings.
- Portfolio ownership is enforced in every portfolio route. Transitional `X-User-ID` remains a
  development-only contract and is not sufficient for public authentication; F11B requires a
  verified LINE/service identity boundary.
- Broker screenshot import remains a private legacy capability and is not part of the public
  controlled demo. Screenshots must not be persisted or committed.
- R1A public web demo uses no portfolio and no database; it reads only a committed synthetic
  fixture. A future authenticated demo with storage would require a physically separate demo
  environment.
- M4 news ingestion stores only public source metadata, traceable URLs and short plain-text excerpts. It does not retain raw RSS HTML or full article content.
- Routine news ingestion does not call Perplexity, Gemini, or another LLM and does not require API credentials.
- FinBERT runs locally on the retained title and short excerpt. M5 sends no article, portfolio, identifier, or prompt to an inference API.
- Model weights and Hugging Face caches are local generated artifacts under ignored paths and must not be committed.
