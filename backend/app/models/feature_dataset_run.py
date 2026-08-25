import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, utc_now


class FeatureDatasetRun(Base):
    __tablename__ = "feature_dataset_runs"
    __table_args__ = (UniqueConstraint("dataset_sha256", name="uq_feature_dataset_runs_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_version: Mapped[str] = mapped_column(String(30), index=True)
    config_sha256: Mapped[str] = mapped_column(String(64), index=True)
    market_snapshot_sha256: Mapped[str] = mapped_column(String(64))
    sentiment_snapshot_sha256: Mapped[str] = mapped_column(String(64))
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    market_source: Mapped[str] = mapped_column(String(30))
    sentiment_model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    row_count: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="succeeded", index=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
