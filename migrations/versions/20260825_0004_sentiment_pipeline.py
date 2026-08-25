"""Create sentiment inference and daily aggregate tables.

Revision ID: 20260825_0004
Revises: 20260825_0003
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0004"
down_revision: str | None = "20260825_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sentiment_inference_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("pipeline_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("candidate_pairs", sa.Integer(), nullable=False),
        sa.Column("scored_pairs", sa.Integer(), nullable=False),
        sa.Column("existing_pairs", sa.Integer(), nullable=False),
        sa.Column("skipped_language_pairs", sa.Integer(), nullable=False),
        sa.Column("aggregate_rows", sa.Integer(), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sentiment_inference_runs_model_version",
        "sentiment_inference_runs",
        ["model_version"],
    )
    op.create_index(
        "ix_sentiment_inference_runs_status", "sentiment_inference_runs", ["status"]
    )

    op.create_table(
        "sentiment_results",
        sa.Column("article_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("positive_prob", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("neutral_prob", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("negative_prob", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("predicted_label", sa.String(length=10), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "ticker", "model_version"),
    )
    op.create_index(
        "ix_sentiment_results_ticker_scored",
        "sentiment_results",
        ["ticker", "scored_at"],
    )

    op.create_table(
        "daily_sentiment_aggregates",
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("sentiment_date", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("positive_prob_mean", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("neutral_prob_mean", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("negative_prob_mean", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("sentiment_score_mean", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("relevance_weighted_score", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("positive_ratio", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("negative_ratio", sa.Numeric(precision=9, scale=8), nullable=False),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("ticker", "sentiment_date", "model_version"),
    )


def downgrade() -> None:
    op.drop_table("daily_sentiment_aggregates")
    op.drop_index("ix_sentiment_results_ticker_scored", table_name="sentiment_results")
    op.drop_table("sentiment_results")
    op.drop_index("ix_sentiment_inference_runs_status", table_name="sentiment_inference_runs")
    op.drop_index(
        "ix_sentiment_inference_runs_model_version", table_name="sentiment_inference_runs"
    )
    op.drop_table("sentiment_inference_runs")
