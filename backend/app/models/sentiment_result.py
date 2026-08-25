from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, utc_now


class SentimentResult(Base):
    __tablename__ = "sentiment_results"
    __table_args__ = (
        Index("ix_sentiment_results_ticker_scored", "ticker", "scored_at"),
    )

    article_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True
    )
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(128), primary_key=True)
    positive_prob: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    neutral_prob: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    negative_prob: Mapped[Decimal] = mapped_column(Numeric(9, 8))
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(10, 8))
    predicted_label: Mapped[str] = mapped_column(String(10))
    input_hash: Mapped[str] = mapped_column(String(64))
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

