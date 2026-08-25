from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    ArticleTicker,
    DailyFeature,
    FeatureDatasetRun,
    MarketPrice,
    NewsArticle,
    SentimentResult,
)


class FeatureRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_prices(
        self,
        *,
        tickers: list[str],
        start_date: date,
        end_date: date,
        source: str,
    ) -> list[MarketPrice]:
        statement = (
            select(MarketPrice)
            .where(
                MarketPrice.ticker.in_(tickers),
                MarketPrice.trading_date >= start_date,
                MarketPrice.trading_date <= end_date,
                MarketPrice.source == source,
            )
            .order_by(MarketPrice.ticker, MarketPrice.trading_date)
        )
        return list(self.session.scalars(statement))

    def list_sentiment(
        self,
        *,
        tickers: list[str],
        start: datetime,
        end: datetime,
        model_version: str,
    ) -> list[tuple[SentimentResult, NewsArticle, ArticleTicker]]:
        rows = self.session.execute(
            select(SentimentResult, NewsArticle, ArticleTicker)
            .join(NewsArticle, NewsArticle.id == SentimentResult.article_id)
            .join(
                ArticleTicker,
                (ArticleTicker.article_id == SentimentResult.article_id)
                & (ArticleTicker.ticker == SentimentResult.ticker),
            )
            .where(
                SentimentResult.ticker.in_(tickers),
                SentimentResult.model_version == model_version,
                NewsArticle.published_at >= start.astimezone(UTC),
                NewsArticle.published_at < end.astimezone(UTC),
            )
            .order_by(NewsArticle.published_at, NewsArticle.id, SentimentResult.ticker)
        )
        return list(rows.tuples())

    def find_run_by_hash(self, dataset_sha256: str) -> FeatureDatasetRun | None:
        return self.session.scalar(
            select(FeatureDatasetRun).where(FeatureDatasetRun.dataset_sha256 == dataset_sha256)
        )

    def add_dataset(self, run: FeatureDatasetRun, rows: list[DailyFeature]) -> None:
        self.session.add(run)
        self.session.flush()
        for row in rows:
            row.dataset_run_id = run.id
        self.session.add_all(rows)

    def list_features(self, dataset_run_id: str) -> list[DailyFeature]:
        statement = (
            select(DailyFeature)
            .where(DailyFeature.dataset_run_id == dataset_run_id)
            .order_by(DailyFeature.feature_date, DailyFeature.ticker)
        )
        return list(self.session.scalars(statement))
