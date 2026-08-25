"""Create users, portfolios, holdings, and sync operations.

Revision ID: 20260825_0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("line_user_id_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("daily_research_limit", sa.Integer(), nullable=False),
        sa.Column("daily_push_enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_line_user_id_hash", "users", ["line_user_id_hash"], unique=True)

    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_portfolio_user_name"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"], unique=False)

    op.create_table(
        "holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("portfolio_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("cost_basis", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("take_profit_pct", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("stop_loss_pct", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "ticker", name="uq_holding_portfolio_ticker"),
    )
    op.create_index("ix_holdings_portfolio_id", "holdings", ["portfolio_id"], unique=False)

    op.create_table(
        "portfolio_sync_operations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("portfolio_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_portfolio_sync_operations_portfolio_id",
        "portfolio_sync_operations",
        ["portfolio_id"],
        unique=False,
    )
    op.create_index(
        "ix_portfolio_sync_operations_status",
        "portfolio_sync_operations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_sync_operations_status", table_name="portfolio_sync_operations")
    op.drop_index(
        "ix_portfolio_sync_operations_portfolio_id",
        table_name="portfolio_sync_operations",
    )
    op.drop_table("portfolio_sync_operations")
    op.drop_index("ix_holdings_portfolio_id", table_name="holdings")
    op.drop_table("holdings")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index("ix_users_line_user_id_hash", table_name="users")
    op.drop_table("users")
