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

Public examples and test fixtures must use synthetic values. Market, news, sentiment, feature, prediction, and research-request definitions remain reserved for their corresponding milestones.
