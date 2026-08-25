from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, utc_now


class DailySentimentAggregate(Base):
    __tablename__ = "daily_sentiment_aggregates"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    sentiment_date: Mapped[date] = mapped_column(Date, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(128), primary_key=True)
    article_count: Mapped[int] = mapped_column(Integer)
    positive_prob_mean: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    neutral_prob_mean: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    negative_prob_mean: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    sentiment_score_mean: Mapped[Decimal] = mapped_column(Numeric(10, 8))
    relevance_weighted_score: Mapped[Decimal] = mapped_column(Numeric(10, 8))
    positive_ratio: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    negative_ratio: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    aggregated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

