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
- `published_at`, `fetched_at`: publication and retrieval timestamps normalized to UTC before persistence; consumers explicitly convert to the required market timezone.
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

### sentiment_results

- `article_id`, `ticker`, `model_version`: composite identity; permits multiple pinned models without overwriting prior research.
- `positive_prob`, `neutral_prob`, `negative_prob`: softmax probabilities stored to eight decimal places.
- `sentiment_score`: `positive_prob - negative_prob`, ranging from `-1` to `1`.
- `predicted_label`: probability argmax; downstream research should still use all probabilities.
- `input_hash`: SHA-256 of exact inference text plus model version.
- `scored_at`: UTC inference timestamp.

### daily_sentiment_aggregates

- `ticker`, `sentiment_date`, `model_version`: composite identity. M5 uses an Asia/Taipei calendar date, not yet a trading-session assignment.
- `article_count`: included article-ticker result count.
- `positive_prob_mean`, `neutral_prob_mean`, `negative_prob_mean`: daily arithmetic means.
- `sentiment_score_mean`: unweighted daily score mean.
- `relevance_weighted_score`: score weighted by M4 article-ticker relevance.
- `positive_ratio`, `negative_ratio`: argmax-label proportions.
- `aggregated_at`: UTC aggregation timestamp.

### sentiment_inference_runs

- `id`, `model_version`, `pipeline_version`: run identity and fixed contracts (`sentiment-v1`).
- `status`: `running`, `succeeded`, or `failed`.
- `candidate_pairs`, `scored_pairs`, `existing_pairs`: idempotency and throughput counts.
- `skipped_language_pairs`: unsupported article-ticker pairs; these receive no fake probabilities.
- `aggregate_rows`: rebuilt daily aggregate count.
- `quality_report`: supported languages, translation policy and batch size.
- `error_code`: exception class only.
- `started_at`, `completed_at`: UTC lifecycle timestamps.

### feature_dataset_runs

- `id`: operational UUID; excluded from the reproducible dataset hash.
- `pipeline_version`: feature contract version, currently `features-v1`.
- `config_sha256`: canonical hash of tickers, date range, providers, model version, timezone and cutoff.
- `market_snapshot_sha256`, `sentiment_snapshot_sha256`: hashes of the exact normalized source rows consumed by the builder.
- `dataset_sha256`: unique canonical hash of configuration, source hashes and ordered modeling rows.
- `market_source`, `sentiment_model_version`: pinned upstream identities. Sentiment version may be null for market-only datasets.
- `start_date`, `end_date`: inclusive source/query contract.
- `row_count`: usable labeled rows after warm-up and final unlabeled-session exclusion.
- `config`: complete non-secret reconstruction configuration.
- `status`, `error_code`, `created_at`: operational metadata.

### daily_features

- `dataset_run_id`, `ticker`, `feature_date`: composite row identity.
- `target_date`: next observed trading session; always later than `feature_date`.
- `information_cutoff`: UTC representation of the local market-close cutoff.
- `latest_sentiment_published_at`: latest publication used by any 1/3/5-session sentiment feature; null when none was used and never later than the cutoff.
- `features`: versioned JSON numeric feature map defined in `docs/feature_definitions.md`. Missing sentiment values remain null.
- `forward_return_1d`: next observed session adjusted-close return.
- `label_up`: `1` for a strictly positive forward return, otherwise `0`.

Prediction and research-request definitions remain reserved for their corresponding milestones.
