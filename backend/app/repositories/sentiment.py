from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models import (
    ArticleTicker,
    DailySentimentAggregate,
    NewsArticle,
    SentimentResult,
)


@dataclass(frozen=True)
class ArticleTickerPair:
    article: NewsArticle
    link: ArticleTicker


class SentimentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_article_ticker_pairs(self) -> list[ArticleTickerPair]:
        rows = self.session.execute(
            select(NewsArticle, ArticleTicker)
            .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
            .order_by(NewsArticle.published_at, NewsArticle.id, ArticleTicker.ticker)
        )
        return [ArticleTickerPair(article, link) for article, link in rows]

    def existing_pair_keys(self, model_version: str) -> set[tuple[str, str]]:
        rows = self.session.execute(
            select(SentimentResult.article_id, SentimentResult.ticker).where(
                SentimentResult.model_version == model_version
            )
        )
        return set(rows.tuples())

    def add_result(self, result: SentimentResult) -> None:
        self.session.add(result)

    def replace_aggregates(
        self, model_version: str, rows: list[DailySentimentAggregate]
    ) -> None:
        self.session.execute(
            delete(DailySentimentAggregate).where(
                DailySentimentAggregate.model_version == model_version
            )
        )
        self.session.add_all(rows)

    def rows_for_aggregation(
        self, model_version: str
    ) -> list[tuple[SentimentResult, NewsArticle, ArticleTicker]]:
        rows = self.session.execute(
            select(SentimentResult, NewsArticle, ArticleTicker)
            .join(NewsArticle, NewsArticle.id == SentimentResult.article_id)
            .join(
                ArticleTicker,
                (ArticleTicker.article_id == SentimentResult.article_id)
                & (ArticleTicker.ticker == SentimentResult.ticker),
            )
            .where(SentimentResult.model_version == model_version)
        )
        return list(rows.tuples())

    def list_daily(
        self,
        *,
        ticker: str,
        start_date: date,
        end_date: date,
        model_version: str,
    ) -> list[DailySentimentAggregate]:
        statement = (
            select(DailySentimentAggregate)
            .where(
                DailySentimentAggregate.ticker == ticker,
                DailySentimentAggregate.sentiment_date >= start_date,
                DailySentimentAggregate.sentiment_date <= end_date,
                DailySentimentAggregate.model_version == model_version,
            )
            .order_by(DailySentimentAggregate.sentiment_date)
        )
        return list(self.session.scalars(statement))

    def list_results(
        self,
        *,
        ticker: str,
        start: datetime,
        end: datetime,
        model_version: str,
    ) -> list[SentimentResult]:
        statement = (
            select(SentimentResult)
            .join(NewsArticle, NewsArticle.id == SentimentResult.article_id)
            .where(
                SentimentResult.ticker == ticker,
                NewsArticle.published_at >= start,
                NewsArticle.published_at < end,
                SentimentResult.model_version == model_version,
            )
            .order_by(NewsArticle.published_at)
        )
        return list(self.session.scalars(statement))
