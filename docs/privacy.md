# Privacy and Secret Handling

Do not commit credentials, identifiers, real portfolios, broker screenshots, import CSV files, or personal data. Local secrets belong only in ignored environment files; public research inputs must be example, synthetic, or anonymized data.

- Raw LINE user IDs must not be stored; account mapping uses a one-way hash.
- The local database, `imports/`, `uploads/`, `user_data/`, and private/raw data paths are Git-ignored.
- Request validation errors omit submitted values.
- Application logs must not include tokens, images, full holdings payloads, or LLM prompts containing private holdings.
- Portfolio ownership is enforced in every M2 route. Transitional `X-User-ID` is not sufficient for public authentication and must be replaced in M10.
- Broker screenshots are not supported or persisted in this iteration.
- Public demo data must use a physically separate demo portfolio/database environment.
- M4 news ingestion stores only public source metadata, traceable URLs and short plain-text excerpts. It does not retain raw RSS HTML or full article content.
- Routine news ingestion does not call Perplexity, Gemini, or another LLM and does not require API credentials.
- FinBERT runs locally on the retained title and short excerpt. M5 sends no article, portfolio, identifier, or prompt to an inference API.
- Model weights and Hugging Face caches are local generated artifacts under ignored paths and must not be committed.
