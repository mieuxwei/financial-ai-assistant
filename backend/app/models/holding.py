import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin


class Holding(TimestampMixin, Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_holding_portfolio_ticker"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    take_profit_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("20"))
    stop_loss_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("-10"))

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")


from backend.app.models.portfolio import Portfolio  # noqa: E402
