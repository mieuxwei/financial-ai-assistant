import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin


class Portfolio(TimestampMixin, Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_portfolio_user_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), default="default")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    sync_operations: Mapped[list["PortfolioSyncOperation"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )


from backend.app.models.holding import Holding  # noqa: E402
from backend.app.models.sync_operation import PortfolioSyncOperation  # noqa: E402
from backend.app.models.user import User  # noqa: E402
