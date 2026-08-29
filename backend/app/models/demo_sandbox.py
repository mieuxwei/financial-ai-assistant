from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, utc_now


class DemoPrincipal(TimestampMixin, Base):
    __tablename__ = "demo_principals"

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    disclosure_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    holdings: Mapped[list[DemoHolding]] = relationship(
        back_populates="principal", cascade="all, delete-orphan"
    )
    idempotency_records: Mapped[list[DemoIdempotencyRecord]] = relationship(
        back_populates="principal", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[DemoAuditEvent]] = relationship(
        back_populates="principal", cascade="all, delete-orphan"
    )


class DemoHolding(TimestampMixin, Base):
    __tablename__ = "demo_holdings"
    __table_args__ = (
        UniqueConstraint("principal_id", "ticker", name="uq_demo_holding_principal_ticker"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    principal_id: Mapped[str] = mapped_column(
        ForeignKey("demo_principals.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(10))
    shares: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    average_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    principal: Mapped[DemoPrincipal] = relationship(back_populates="holdings")


class DemoIdempotencyRecord(Base):
    __tablename__ = "demo_idempotency_records"
    __table_args__ = (
        UniqueConstraint("principal_id", "idempotency_key", name="uq_demo_principal_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    principal_id: Mapped[str] = mapped_column(
        ForeignKey("demo_principals.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(80))
    response_payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    principal: Mapped[DemoPrincipal] = relationship(back_populates="idempotency_records")


class DemoAuditEvent(Base):
    __tablename__ = "demo_audit_events"
    __table_args__ = (Index("ix_demo_audit_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    principal_id: Mapped[str] = mapped_column(
        ForeignKey("demo_principals.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    principal: Mapped[DemoPrincipal] = relationship(back_populates="audit_events")
