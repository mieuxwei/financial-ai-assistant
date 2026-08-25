from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    ArticleTicker,
    DailyFeature,
    FeatureDatasetRun,
    MarketPrice,
    NewsArticle,
    SentimentResult,
)
from backend.app.services.features import FeatureDatasetService
from pipelines.features.types import FeatureConfig


def add_fixture_rows(session: Session) -> tuple[date, date]:
    start = date(2026, 1, 1)
    dates = [start + timedelta(days=index) for index in range(32)]
    session.add_all(
        [
            MarketPrice(
                ticker="2330",
                trading_date=trading_date,
                source="fixture",
                open=Decimal(99 + index),
                high=Decimal(101 + index),
                low=Decimal(98 + index),
                close=Decimal(100 + index),
                adjusted_close=Decimal(100 + index),
                volume=1000 + index,
            )
            for index, trading_date in enumerate(dates)
        ]
    )
    article = NewsArticle(
        title="Profit increased",
        published_at=datetime(2026, 1, 26, 4, tzinfo=UTC),
        fetched_at=datetime(2026, 1, 26, 4, tzinfo=UTC),
        source="fixture",
        source_type="official_announcement",
        url="https://example.com/feature-fixture",
        canonical_url="https://example.com/feature-fixture",
        summary="Synthetic test fixture.",
        content_hash="f" * 64,
        title_fingerprint="e" * 64,
        language="en",
    )
    session.add(article)
    session.flush()
    session.add(
        ArticleTicker(
            article_id=article.id,
            ticker="2330",
            relevance_score=Decimal("1"),
            match_method="fixture",
        )
    )
    session.add(
        SentimentResult(
            article_id=article.id,
            ticker="2330",
            model_version="fixture-model@revision",
            positive_prob=Decimal("0.8"),
            neutral_prob=Decimal("0.15"),
            negative_prob=Decimal("0.05"),
            sentiment_score=Decimal("0.75"),
            predicted_label="positive",
            input_hash="d" * 64,
        )
    )
    session.commit()
    return dates[0], dates[-1]


def test_dataset_build_is_persisted_versioned_and_idempotent(db_session: Session) -> None:
    start, end = add_fixture_rows(db_session)
    config = FeatureConfig(
        tickers=("2330",),
        start_date=start,
        end_date=end,
        market_source="fixture",
        sentiment_model_version="fixture-model@revision",
    )
    service = FeatureDatasetService(db_session)

    first = service.build(config)
    second = service.build(config)

    assert first.row_count == 6
    assert first.dataset_sha256 == second.dataset_sha256
    assert first.dataset_run_id == second.dataset_run_id
    assert first.reused is False
    assert second.reused is True
    assert db_session.scalar(select(func.count()).select_from(FeatureDatasetRun)) == 1
    assert db_session.scalar(select(func.count()).select_from(DailyFeature)) == 6
    stored = list(db_session.scalars(select(DailyFeature).order_by(DailyFeature.feature_date)))
    assert all(row.target_date > row.feature_date for row in stored)
    assert all(
        row.latest_sentiment_published_at is None
        or row.latest_sentiment_published_at <= row.information_cutoff
        for row in stored
    )
