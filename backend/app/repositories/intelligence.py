from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.app.models import ArticleTicker, NewsArticle, SentimentResult


@dataclass(frozen=True)
class IntelligenceSourceRow:
    article: NewsArticle
    link: ArticleTicker
    sentiment: SentimentResult | None


class IntelligenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent(
        self,
        *,
        ticker: str,
        model_version: str,
        limit: int,
        as_of_cutoff: datetime | None,
    ) -> list[IntelligenceSourceRow]:
        statement = (
            select(NewsArticle, ArticleTicker, SentimentResult)
            .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
            .outerjoin(
                SentimentResult,
                and_(
                    SentimentResult.article_id == NewsArticle.id,
                    SentimentResult.ticker == ArticleTicker.ticker,
                    SentimentResult.model_version == model_version,
                ),
            )
            .where(ArticleTicker.ticker == ticker)
            .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
            .limit(limit)
        )
        if as_of_cutoff is not None:
            statement = statement.where(NewsArticle.published_at <= as_of_cutoff)
        rows = self.session.execute(statement)
        return [IntelligenceSourceRow(*row) for row in rows.tuples()]
