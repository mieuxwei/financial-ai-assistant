from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class DailyFeature(Base):
    __tablename__ = "daily_features"

    dataset_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("feature_dataset_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    feature_date: Mapped[date] = mapped_column(Date, primary_key=True)
    target_date: Mapped[date] = mapped_column(Date)
    information_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latest_sentiment_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    features: Mapped[dict[str, float | int | None]] = mapped_column(JSON)
    forward_return_1d: Mapped[Decimal] = mapped_column(Numeric(14, 10))
    label_up: Mapped[int] = mapped_column(Integer)
