"""Create versioned feature datasets and daily features.

Revision ID: 20260825_0005
Revises: 20260825_0004
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0005"
down_revision: str | None = "20260825_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_dataset_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_version", sa.String(length=30), nullable=False),
        sa.Column("config_sha256", sa.String(length=64), nullable=False),
        sa.Column("market_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("sentiment_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset_sha256", sa.String(length=64), nullable=False),
        sa.Column("market_source", sa.String(length=30), nullable=False),
        sa.Column("sentiment_model_version", sa.String(length=128), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_sha256", name="uq_feature_dataset_runs_sha256"),
    )
    op.create_index(
        "ix_feature_dataset_runs_pipeline_version",
        "feature_dataset_runs",
        ["pipeline_version"],
    )
    op.create_index(
        "ix_feature_dataset_runs_config_sha256",
        "feature_dataset_runs",
        ["config_sha256"],
    )
    op.create_index("ix_feature_dataset_runs_status", "feature_dataset_runs", ["status"])
    op.create_table(
        "daily_features",
        sa.Column("dataset_run_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("feature_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("information_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_sentiment_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("forward_return_1d", sa.Numeric(precision=14, scale=10), nullable=False),
        sa.Column("label_up", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_run_id"], ["feature_dataset_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("dataset_run_id", "ticker", "feature_date"),
    )


def downgrade() -> None:
    op.drop_table("daily_features")
    op.drop_index("ix_feature_dataset_runs_status", table_name="feature_dataset_runs")
    op.drop_index("ix_feature_dataset_runs_config_sha256", table_name="feature_dataset_runs")
    op.drop_index("ix_feature_dataset_runs_pipeline_version", table_name="feature_dataset_runs")
    op.drop_table("feature_dataset_runs")
