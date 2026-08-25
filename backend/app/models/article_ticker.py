from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class ArticleTicker(Base):
    __tablename__ = "article_tickers"

    article_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True
    )
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    match_method: Mapped[str] = mapped_column(String(40))

