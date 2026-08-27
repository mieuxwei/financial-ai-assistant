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

### sentiment_results (physical M5 table; logical English sentiment output)

- `article_id`, `ticker`, `model_version`: composite identity; permits multiple pinned models without overwriting prior research.
- `positive_prob`, `neutral_prob`, `negative_prob`: softmax probabilities stored to eight decimal places.
- `sentiment_score`: `positive_prob - negative_prob`, ranging from `-1` to `1`.
- `predicted_label`: probability argmax; downstream research should still use all probabilities.
- `input_hash`: SHA-256 of exact inference text plus model version.
- `scored_at`: UTC inference timestamp.

Only the pinned English FinBERT track writes probability outputs to this table. The longer-term
logical contract is named `english_sentiment_results`; Chinese/Taiwan weak signals must not be
inserted here or presented as comparable human-validated sentiment.

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

## Track A M1–M2 local artifact contracts

These immutable research artifacts live in Git-ignored `.tools/` storage and are not database
migrations or public raw datasets.

### risk-market-dataset-v1

- `config`: fixed universe, provider identities, timezone, and chronological date boundaries.
- `benchmark_rows`, `stock_rows`: normalized local provider observations with split metadata.
- `benchmark_snapshot_sha256`, `sha256`: upstream and complete-dataset lineage.
- `sealed_test_outcomes_inspected`, `risk_labels_generated`, `models_trained`: false in M1.

### next-session-volatility-risk-labels-v1

- `ticker`, `feature_session`, `information_cutoff`: post-close prediction identity at `t`.
- `target_session`: exact next benchmark exchange session `t+1`.
- `split`: train or validation only in M2; test is not materialized.
- `feature_state_sha256`: commitment to the complete `t`-known history used for the trailing scale.
- `trailing_volatility_scale`: population standard deviation of 20 consecutive one-session
  adjusted-close log returns ending at `t`.
- `continuous_risk_outcome`: absolute `t` to `t+1` adjusted-close log return divided by the trailing
  scale.
- `next_abs_log_return`, `next_high_low_log_range`, `next_parkinson_volatility`: secondary
  continuous robustness outcomes.
- `risk_threshold`, `risk_threshold_sha256`: training-only candidate threshold and immutable
  artifact identity.
- `risk_label`: `NORMAL` or `HIGH_RISK`; not direction, causation, or investment advice.
- `market_dataset_sha256`, `protocol_config_sha256`, `sha256`: complete input/config/output lineage.

### risk-feature-dataset-v1

- `ticker`, `feature_session`, `information_cutoff`, `split`: prediction identity; M3 contains
  train/validation only.
- `features`: exactly 23 finite fields defined by `docs/risk_feature_protocol.md`, all ending at
  `t`; no target-side field is allowed inside this mapping.
- `feature_values_sha256`: hash of ticker/session/cutoff and the complete ordered feature mapping.
- `label_row_sha256`: commitment to the separately stored M2 target row.
- `target`: target session, continuous risk/robustness outcomes, risk label and threshold artifact
  hash; structurally separate from features.
- `config_sha256`, `market_dataset_sha256`, `risk_label_dataset_sha256`, `sha256`: reconstruction
  lineage.
- `sealed_test_features_materialized`, `preprocessing_fitted`, `models_trained`: false in M3.

## Planned zero-manual-label Taiwan research tables

These are logical contracts for M7–M10, not implemented database migrations in the current
milestone.

### english_sentiment_results

- `article_id`, `ticker`, `model_version`: stable identity, compatible with the existing physical
  `sentiment_results` table.
- `positive_prob`, `neutral_prob`, `negative_prob`, `sentiment_score`, `predicted_label`: pinned
  English FinBERT outputs only.
- `input_hash`, `scored_at`: exact-input lineage and operational time.

### taiwan_text_signals

- `article_id`, `event_group_id`, `ticker`: traceable text/event identity.
- `official_source_category`: source-provided category retained exactly; never replaced by model
  inference.
- `normalized_event_type`: automatically inferred taxonomy value, stored separately from the
  official category.
- `source_type`, `language`, `effective_session`: availability and alignment metadata.
- `representation_model_version`, `representation_vector_ref`: pinned encoder identity and
  immutable vector artifact reference; vectors are not human labels.
- `weak_label`, `weak_confidence`: aggregated automated signal and confidence, never ground truth.
- `labeling_function_versions`, `agreement`, `vote_entropy`: reproducible weak-source provenance.
- `abstained`, `abstention_reason`, `coverage_state`: explicit missing/disagreement behavior.
- `encoder_revision`, `protocol_version`, `model_versions`, `prompt_hashes`, `input_hash`: complete
  reproducibility contract.
- `generated_at`: operational timestamp; excluded from semantic snapshot identity.

### market_reaction_labels

- `event_group_id`, `ticker`, `published_at`: event-side identity and original availability time.
- `timezone`, `information_cutoff`, `effective_session`, `anchor_session`, `end_session`, `horizon`:
  exchange-calendar alignment contract.
- `raw_return`, `benchmark_return`, `abnormal_return`: mechanically calculated continuous targets.
- `reaction_class`, `neutral_threshold`, `threshold_version`: automatic class and frozen rule.
- `benchmark_id`, `market_snapshot_sha256`: benchmark and immutable price lineage.
- `ticker_session_information_set`: groups same-ticker same-session events when individual causal
  attribution is impossible.
- `split_assignment`, `protocol_version`: chronological isolation and calculation version.
- `abstention_reason`, `missing_reason`: timestamp, price, corporate-action or quality failures;
  missing values are never silently filled.

Future reaction values are target-side data. A downstream row may use only reaction statistics for
older events whose complete reaction window ended before that row's information cutoff.

The M8 v1 physical output is currently immutable split-separated JSONL in ignored `.tools/`
storage, not a database migration. Its machine report records snapshot hashes, row/abstention counts
and readiness status while withholding sealed-test class metrics. The first bounded snapshot has no
train or validation rows and is not eligible for downstream fitting.

### M9 weak-vote artifact contract

- `labeling_function_id`, `labeling_function_revision`, `source_type`: independent automated source
  identity; one vote per function and input.
- `impact_label`, `normalized_event_type`, `confidence`, `abstention_reason`: silver signal only.
- `input_sha256`, `model_version`, `prompt_sha256`: exact provenance required as applicable.
- Aggregate output retains `official_source_category` separately and adds weak label/confidence,
  inferred event type, coverage, agreement, vote entropy, function revisions, model/prompt hashes
  and `vote_snapshot_sha256`.
- `manual_labels_used`, `manual_review_used`, `sentiment_ground_truth`: always false in this
  protocol. Insufficient or conflicting evidence is never silently filled as neutral.
