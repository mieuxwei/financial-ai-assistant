import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, utc_now


class SentimentInferenceRun(Base):
    __tablename__ = "sentiment_inference_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version: Mapped[str] = mapped_column(String(128), index=True)
    pipeline_version: Mapped[str] = mapped_column(String(30), default="sentiment-v1")
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    candidate_pairs: Mapped[int] = mapped_column(Integer, default=0)
    scored_pairs: Mapped[int] = mapped_column(Integer, default=0)
    existing_pairs: Mapped[int] = mapped_column(Integer, default=0)
    skipped_language_pairs: Mapped[int] = mapped_column(Integer, default=0)
    aggregate_rows: Mapped[int] = mapped_column(Integer, default=0)
    quality_report: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

