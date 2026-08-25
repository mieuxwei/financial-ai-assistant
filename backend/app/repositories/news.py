from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import ArticleTicker, NewsArticle
from pipelines.news.normalization import fuzzy_title_similarity
from pipelines.news.types import TickerMatch


class NewsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_exact(self, content_hash: str) -> NewsArticle | None:
        return self.session.scalar(
            select(NewsArticle).where(NewsArticle.content_hash == content_hash)
        )

    def find_fuzzy(
        self,
        *,
        title: str,
        published_at: datetime,
        threshold: float = 0.92,
    ) -> NewsArticle | None:
        start = published_at - timedelta(days=2)
        end = published_at + timedelta(days=2)
        statement = select(NewsArticle).where(
                NewsArticle.published_at >= start,
                NewsArticle.published_at <= end,
            )
        candidates = self.session.scalars(statement)
        return next(
            (
                article
                for article in candidates
                if fuzzy_title_similarity(title, article.title) >= threshold
            ),
            None,
        )

    def add_article(self, article: NewsArticle, matches: list[TickerMatch]) -> None:
        self.session.add(article)
        self.session.flush()
        self.session.add_all(
            [
                ArticleTicker(
                    article_id=article.id,
                    ticker=match.ticker,
                    relevance_score=match.relevance_score,
                    match_method=match.match_method,
                )
                for match in matches
            ]
        )
