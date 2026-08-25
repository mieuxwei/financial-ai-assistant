from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import ArticleTicker, NewsArticle, NewsIngestionRun
from backend.app.services.news import NewsIngestionService
from pipelines.news.matching import TickerMatcher
from pipelines.news.types import NewsItem


class FixtureNewsProvider:
    name = "fixture_news"

    def __init__(self, items: list[NewsItem]) -> None:
        self.items = items

    def fetch(self) -> list[NewsItem]:
        return self.items


class FailingNewsProvider:
    name = "failing_news"

    def fetch(self) -> list[NewsItem]:
        raise RuntimeError("synthetic provider failure")


def make_item(title: str, url: str, *, minute: int = 0) -> NewsItem:
    return NewsItem(
        title=title,
        published_at=datetime(2026, 8, 25, 8, minute, tzinfo=UTC),
        source="fixture_news",
        source_type="official_rss",
        url=url,
        summary="只保存短摘要，提及台積電。",
        external_id=url.rsplit("/", 1)[-1],
    )


def test_repeated_ingestion_and_fuzzy_variant_do_not_duplicate(db_session: Session) -> None:
    provider = FixtureNewsProvider(
        [
            make_item("台積電董事會重要決議", "https://example.com/1"),
            make_item("台積電：董事會重要決議", "https://example.com/2", minute=1),
        ]
    )
    service = NewsIngestionService(
        db_session, provider, TickerMatcher({"2330": ("台積電",)})
    )

    first = service.ingest()
    second = service.ingest()

    assert first.records_inserted == 1
    assert first.fuzzy_duplicates == 1
    assert second.records_inserted == 0
    assert second.exact_duplicates == 1
    assert second.fuzzy_duplicates == 1
    assert db_session.scalar(select(func.count()).select_from(NewsArticle)) == 1
    link = db_session.scalar(select(ArticleTicker))
    assert link is not None
    assert link.ticker == "2330"
    assert str(link.relevance_score) == "0.900"


def test_source_traceability_and_run_metrics_are_persisted(db_session: Session) -> None:
    item = make_item("市場制度公告", "https://example.com/source?id=1&utm_source=test")
    result = NewsIngestionService(
        db_session, FixtureNewsProvider([item]), TickerMatcher({"2330": ("台積電",)})
    ).ingest()

    article = db_session.scalar(select(NewsArticle))
    run = db_session.get(NewsIngestionRun, result.run_id)
    assert article is not None and run is not None
    assert article.url.endswith("utm_source=test")
    assert article.canonical_url == "https://example.com/source?id=1"
    assert article.summary == "只保存短摘要，提及台積電。"
    assert run.status == "succeeded"
    assert run.quality_report == {
        "unmatched_articles": 0,
        "summary_max_characters": 500,
        "full_article_content_stored": False,
    }


def test_similar_official_announcements_with_distinct_ids_are_preserved(
    db_session: Session,
) -> None:
    published_at = datetime(2026, 8, 25, 8, tzinfo=UTC)
    items = [
        NewsItem(
            title="代子公司公告董事會重要決議",
            published_at=published_at,
            source="fixture_news",
            source_type="official_announcement",
            url="https://example.com/openapi",
            external_id="company-2330-record",
            explicit_tickers=("2330",),
        ),
        NewsItem(
            title="代子公司公告：董事會重要決議",
            published_at=published_at,
            source="fixture_news",
            source_type="official_announcement",
            url="https://example.com/openapi",
            external_id="company-2330-second-record",
            explicit_tickers=("2330",),
        ),
    ]

    result = NewsIngestionService(
        db_session,
        FixtureNewsProvider(items),
        TickerMatcher({"2330": ("台積電",), "2317": ("鴻海",)}),
    ).ingest()

    assert result.records_inserted == 2
    assert result.fuzzy_duplicates == 0
    assert db_session.scalar(select(func.count()).select_from(NewsArticle)) == 2


def test_provider_failure_records_failed_run_without_articles(db_session: Session) -> None:
    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        NewsIngestionService(
            db_session, FailingNewsProvider(), TickerMatcher({"2330": ("台積電",)})
        ).ingest()

    run = db_session.scalar(select(NewsIngestionRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "RuntimeError"
    assert db_session.scalar(select(func.count()).select_from(NewsArticle)) == 0
