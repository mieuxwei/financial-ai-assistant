# Architecture

## First iteration boundary

The M0–M2 implementation establishes FastAPI, SQLAlchemy/Alembic, user-owned portfolios, and atomic portfolio synchronization. It deliberately does not implement market data, news, sentiment, models, or backtesting.

```text
Transitional trusted caller
  → X-User-ID context
  → FastAPI portfolio API
  → PortfolioService
  → SQLAlchemy repository
  → SQLite (local) / PostgreSQL (deployment target)
```

`X-User-ID` exists only to exercise ownership during the transition. It must not be exposed as standalone authentication. M10 replaces it with identity derived from a verified LINE webhook or another authenticated service boundary.

Portfolio sync uses a short-lived preview operation. Confirm applies additions, updates, and removals in one database transaction and is idempotent.

## Planned system

Future ingestion pipelines will remain separate from feature generation and offline research. The LINE adapter consumes backend contracts and must not become a second source of portfolio, market-data, or research truth.
