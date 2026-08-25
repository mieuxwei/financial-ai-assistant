from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, utc_now


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (Index("ix_market_prices_ticker_date", "ticker", "trading_date"),)

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    trading_date: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(30), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    adjusted_close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
