from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    ArticleTicker,
    DailySentimentAggregate,
    NewsArticle,
    SentimentInferenceRun,
    SentimentResult,
)
from backend.app.repositories.sentiment import SentimentRepository
from backend.app.services.sentiment import SentimentInferenceService
from pipelines.sentiment.types import SentimentPrediction


class FixtureSentimentModel:
    model_version = "fixture-finbert@fixed-revision"
    supported_language_prefixes = ("en",)

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]:
        self.calls.append(texts)
        return [
            SentimentPrediction(0.8, 0.15, 0.05)
            if "profit" in text.casefold()
            else SentimentPrediction(0.05, 0.15, 0.8)
            for text in texts
        ]


class FailingSentimentModel(FixtureSentimentModel):
    def predict_batch(self, texts: list[str]) -> list[SentimentPrediction]:
        raise RuntimeError("synthetic inference failure")


def add_article(
    session: Session,
    *,
    identity: str,
    title: str,
    language: str,
    published_at: datetime,
    tickers: tuple[tuple[str, str], ...],
) -> NewsArticle:
    article = NewsArticle(
        title=title,
        published_at=published_at,
        fetched_at=published_at,
        source="fixture",
        source_type="fixture",
        url=f"https://example.com/{identity}",
        canonical_url=f"https://example.com/{identity}",
        summary="Synthetic research fixture.",
        content_hash=identity.ljust(64, "0"),
        title_fingerprint=identity.rjust(64, "0"),
        language=language,
        external_id=identity,
    )
    session.add(article)
    session.flush()
    session.add_all(
        [
            ArticleTicker(
                article_id=article.id,
                ticker=ticker,
                relevance_score=Decimal(score),
                match_method="fixture",
            )
            for ticker, score in tickers
        ]
    )
    session.commit()
    return article


def test_batch_inference_is_idempotent_and_predicts_unique_articles_once(
    db_session: Session,
) -> None:
    article = add_article(
        db_session,
        identity="english-profit",
        title="Company profit exceeded expectations",
        language="en",
        published_at=datetime(2026, 8, 25, 1, tzinfo=UTC),
        tickers=(("2330", "1.0"), ("0050", "0.65")),
    )
    add_article(
        db_session,
        identity="chinese-news",
        title="公司公布財務報告",
        language="zh-TW",
        published_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
        tickers=(("2330", "1.0"),),
    )
    model = FixtureSentimentModel()
    service = SentimentInferenceService(db_session, model, batch_size=4)

    first = service.run()
    stored = list(db_session.scalars(select(SentimentResult)))
    first_hashes = {row.input_hash for row in stored}
    second = service.run()

    assert first.candidate_pairs == 3
    assert first.scored_pairs == 2
    assert first.skipped_language_pairs == 1
    assert len(model.calls) == 1
    assert len(model.calls[0]) == 1
    assert {row.article_id for row in stored} == {article.id}
    assert {row.predicted_label for row in stored} == {"positive"}
    assert second.scored_pairs == 0
    assert second.existing_pairs == 2
    assert second.skipped_language_pairs == 1
    assert first_hashes == {
        row.input_hash for row in db_session.scalars(select(SentimentResult))
    }
    assert db_session.scalar(select(func.count()).select_from(SentimentResult)) == 2


def test_daily_aggregation_and_ticker_date_queries(db_session: Session) -> None:
    add_article(
        db_session,
        identity="positive",
        title="Profit increased sharply",
        language="en-US",
        published_at=datetime(2026, 8, 24, 23, 30, tzinfo=UTC),
        tickers=(("2330", "1.0"),),
    )
    add_article(
        db_session,
        identity="negative",
        title="Loss widened significantly",
        language="en",
        published_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
        tickers=(("2330", "0.5"),),
    )
    model = FixtureSentimentModel()
    result = SentimentInferenceService(db_session, model, batch_size=1).run()

    repository = SentimentRepository(db_session)
    daily = repository.list_daily(
        ticker="2330",
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 25),
        model_version=model.model_version,
    )
    raw = repository.list_results(
        ticker="2330",
        start=datetime(2026, 8, 24, tzinfo=UTC),
        end=datetime(2026, 8, 26, tzinfo=UTC),
        model_version=model.model_version,
    )

    assert result.aggregate_rows == 1
    assert len(raw) == 2
    assert len(daily) == 1
    assert daily[0].article_count == 2
    assert daily[0].sentiment_score_mean == Decimal("0.00000000")
    assert daily[0].relevance_weighted_score == Decimal("0.25000000")
    assert daily[0].positive_ratio == Decimal("0.50000000")
    assert daily[0].negative_ratio == Decimal("0.50000000")


def test_inference_failure_rolls_back_results_and_records_run(db_session: Session) -> None:
    add_article(
        db_session,
        identity="failure",
        title="Profit increased",
        language="en",
        published_at=datetime(2026, 8, 25, tzinfo=UTC),
        tickers=(("2330", "1.0"),),
    )
    with pytest.raises(RuntimeError, match="synthetic inference failure"):
        SentimentInferenceService(db_session, FailingSentimentModel()).run()

    run = db_session.scalar(select(SentimentInferenceRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "RuntimeError"
    assert db_session.scalar(select(func.count()).select_from(SentimentResult)) == 0
    assert db_session.scalar(select(func.count()).select_from(DailySentimentAggregate)) == 0
