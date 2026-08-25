# Data Dictionary

## M1–M2 tables

### users

- `id`: internal UUID string; never a raw LINE identifier.
- `line_user_id_hash`: unique one-way identifier used for account mapping.
- `status`: lifecycle status.
- `daily_research_limit`: future on-demand research allowance; default 5.
- `daily_push_enabled`: daily notification preference.
- `created_at`: UTC creation time.

### portfolios

- `id`: internal UUID string.
- `user_id`: owning user foreign key.
- `name`: portfolio name; M2 uses `default`.
- `is_demo`: separates example data from a private portfolio.
- `created_at`, `updated_at`: UTC audit timestamps.

### holdings

- `id`: internal UUID string.
- `portfolio_id`: owning portfolio foreign key.
- `ticker`: normalized ticker without Yahoo market suffix.
- `name`: display name; spreadsheet formula prefixes are rejected.
- `quantity`: positive decimal share quantity.
- `cost_basis`: non-negative decimal average cost.
- `take_profit_pct`, `stop_loss_pct`: user-defined monitoring thresholds, not trade orders.
- `created_at`, `updated_at`: UTC audit timestamps.

### portfolio_sync_operations

- `id`: one-time UUID operation ID.
- `portfolio_id`: target portfolio.
- `status`: `pending`, `confirmed`, or `expired`.
- `payload`: validated replacement holdings, stored only in the private database.
- `payload_hash`: deterministic SHA-256 of the validated preview.
- `created_at`, `expires_at`, `confirmed_at`: operation lifecycle timestamps.

Public examples and test fixtures must use synthetic values. News, sentiment, feature, prediction, and research-request definitions remain reserved for their corresponding milestones.

### market_prices

- `ticker`: canonical ticker; part of the primary key.
- `trading_date`: Asia/Taipei-normalized trading date; part of the primary key.
- `source`: provider name; part of the primary key.
- `open`, `high`, `low`, `close`: normalized positive daily prices.
- `adjusted_close`: provider adjusted close normalized to three decimal places, falling back to normalized close only when unavailable. This removes provider floating-point jitter while preserving material corporate-action revisions.
- `volume`: non-negative daily share volume.
- `ingested_at`: UTC timestamp of the latest successful upsert.

For an existing row, adjusted-close changes of `0.005` or less are treated as provider floating-point jitter and retain the stored value. Larger changes are applied as material revisions.

### market_ingestion_runs

- `id`: UUID run identifier.
- `provider`: provider adapter name.
- `pipeline_version`: normalization and quality-contract version; currently `market-data-v1`.
- `status`: `running`, `succeeded`, or `failed`.
- `tickers`: canonical ticker and provider-symbol mappings used by the run.
- `start_date`, `end_date`: inclusive requested range.
- `records_fetched`, `records_upserted`: normalized row counts.
- `quality_report`: per-ticker ranges, warnings, potential gaps, and fatal issues.
- `error_code`: exception class only; never raw provider payloads or credentials.
- `started_at`, `completed_at`: UTC lifecycle timestamps.

### news_articles

- `id`: internal UUID.
- `title`: provider title; required.
- `published_at`, `fetched_at`: timezone-aware publication and UTC retrieval times.
- `source`: `twse_material` or `twse_news_rss` for the M4 official providers.
- `source_type`: `official_announcement` or `official_rss`.
- `url`: original traceable source URL.
- `canonical_url`: URL after fragment and known tracking parameters are removed.
- `summary`: optional plain-text excerpt limited to 500 characters; never raw RSS HTML/full text.
- `content_hash`: exact deduplication identity derived from normalized title, canonical URL, publication time and provider external ID when available.
- `title_fingerprint`: SHA-256 of the normalized title for reproducibility/audit.
- `language`: provider content language, currently `zh-TW`.
- `external_id`: provider identifier where available.
- `source_metadata`: non-secret source fields such as public company name, disclosure clause and fact date.

### article_tickers

- `article_id`, `ticker`: composite primary key.
- `relevance_score`: deterministic score from `0` to `1`.
- `match_method`: `official_company_code`, `ticker_title`, `company_alias_title`, `ticker_summary`, or `company_alias_summary`.

### news_ingestion_runs

- `id`, `provider`, `pipeline_version`: auditable run identity and contract version (`news-v1`).
- `status`: `running`, `succeeded`, or `failed`.
- `records_fetched`, `records_inserted`: provider and persistence counts.
- `exact_duplicates`, `fuzzy_duplicates`: skipped duplicate counts.
- `ticker_matches`: persisted article-to-ticker link count.
- `quality_report`: unmatched count and content-retention policy flags.
- `error_code`: exception class only; response bodies are not stored.
- `started_at`, `completed_at`: UTC lifecycle timestamps.

Sentiment, feature, prediction, and research-request definitions remain reserved for their corresponding milestones.
