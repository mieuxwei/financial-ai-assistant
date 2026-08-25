"""Create news ingestion tables.

Revision ID: 20260825_0003
Revises: 20260825_0002
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0003"
down_revision: str | None = "20260825_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_ingestion_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("pipeline_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_fetched", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("exact_duplicates", sa.Integer(), nullable=False),
        sa.Column("fuzzy_duplicates", sa.Integer(), nullable=False),
        sa.Column("ticker_matches", sa.Integer(), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_news_ingestion_runs_provider", "news_ingestion_runs", ["provider"])
    op.create_index("ix_news_ingestion_runs_status", "news_ingestion_runs", ["status"])

    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_news_articles_content_hash"),
    )
    op.create_index("ix_news_articles_content_hash", "news_articles", ["content_hash"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])
    op.create_index(
        "ix_news_articles_published_source", "news_articles", ["published_at", "source"]
    )
    op.create_index("ix_news_articles_source", "news_articles", ["source"])
    op.create_index(
        "ix_news_articles_title_fingerprint", "news_articles", ["title_fingerprint"]
    )

    op.create_table(
        "article_tickers",
        sa.Column("article_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("match_method", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "ticker"),
    )
    op.create_index("ix_article_tickers_ticker", "article_tickers", ["ticker"])


def downgrade() -> None:
    op.drop_index("ix_article_tickers_ticker", table_name="article_tickers")
    op.drop_table("article_tickers")
    op.drop_index("ix_news_articles_title_fingerprint", table_name="news_articles")
    op.drop_index("ix_news_articles_source", table_name="news_articles")
    op.drop_index("ix_news_articles_published_source", table_name="news_articles")
    op.drop_index("ix_news_articles_published_at", table_name="news_articles")
    op.drop_index("ix_news_articles_content_hash", table_name="news_articles")
    op.drop_table("news_articles")
    op.drop_index("ix_news_ingestion_runs_status", table_name="news_ingestion_runs")
    op.drop_index("ix_news_ingestion_runs_provider", table_name="news_ingestion_runs")
    op.drop_table("news_ingestion_runs")
