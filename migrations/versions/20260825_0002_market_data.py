"""Create market prices and ingestion runs.

Revision ID: 20260825_0002
Revises: 20260825_0001
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0002"
down_revision: str | None = "20260825_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_ingestion_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("pipeline_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("records_fetched", sa.Integer(), nullable=False),
        sa.Column("records_upserted", sa.Integer(), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_ingestion_runs_provider",
        "market_ingestion_runs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_market_ingestion_runs_status",
        "market_ingestion_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "market_prices",
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("ticker", "trading_date", "source"),
    )
    op.create_index(
        "ix_market_prices_ticker_date",
        "market_prices",
        ["ticker", "trading_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_prices_ticker_date", table_name="market_prices")
    op.drop_table("market_prices")
    op.drop_index("ix_market_ingestion_runs_status", table_name="market_ingestion_runs")
    op.drop_index("ix_market_ingestion_runs_provider", table_name="market_ingestion_runs")
    op.drop_table("market_ingestion_runs")
