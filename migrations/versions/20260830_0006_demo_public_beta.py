"""Create isolated LINE public-beta sandbox tables.

Revision ID: 20260830_0006
Revises: 20260825_0005
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0006"
down_revision: str | None = "20260825_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_principals",
        sa.Column("id", sa.String(length=67), nullable=False),
        sa.Column("disclosure_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_demo_principals_expires_at", "demo_principals", ["expires_at"])

    op.create_table(
        "demo_holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("principal_id", sa.String(length=67), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("shares", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("average_cost", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["demo_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("principal_id", "ticker", name="uq_demo_holding_principal_ticker"),
    )
    op.create_index("ix_demo_holdings_principal_id", "demo_holdings", ["principal_id"])
    op.create_index("ix_demo_holdings_expires_at", "demo_holdings", ["expires_at"])

    op.create_table(
        "demo_idempotency_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("principal_id", sa.String(length=67), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["demo_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "principal_id", "idempotency_key", name="uq_demo_principal_idempotency"
        ),
    )
    op.create_index(
        "ix_demo_idempotency_records_principal_id",
        "demo_idempotency_records",
        ["principal_id"],
    )

    op.create_table(
        "demo_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("principal_id", sa.String(length=67), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["demo_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_demo_audit_events_principal_id", "demo_audit_events", ["principal_id"])
    op.create_index("ix_demo_audit_created_at", "demo_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_demo_audit_created_at", table_name="demo_audit_events")
    op.drop_index("ix_demo_audit_events_principal_id", table_name="demo_audit_events")
    op.drop_table("demo_audit_events")
    op.drop_index(
        "ix_demo_idempotency_records_principal_id", table_name="demo_idempotency_records"
    )
    op.drop_table("demo_idempotency_records")
    op.drop_index("ix_demo_holdings_expires_at", table_name="demo_holdings")
    op.drop_index("ix_demo_holdings_principal_id", table_name="demo_holdings")
    op.drop_table("demo_holdings")
    op.drop_index("ix_demo_principals_expires_at", table_name="demo_principals")
    op.drop_table("demo_principals")
