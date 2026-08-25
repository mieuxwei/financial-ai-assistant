import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    line_user_id_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    daily_research_limit: Mapped[int] = mapped_column(Integer, default=5)
    daily_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    portfolios: Mapped[list["Portfolio"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


from backend.app.models.portfolio import Portfolio  # noqa: E402
