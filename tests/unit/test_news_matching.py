from datetime import UTC, datetime

from pipelines.news.matching import TickerMatcher
from pipelines.news.types import NewsItem


def make_item(title: str, summary: str | None = None, explicit=()) -> NewsItem:
    return NewsItem(
        title=title,
        summary=summary,
        published_at=datetime(2026, 8, 25, tzinfo=UTC),
        source="fixture",
        source_type="fixture",
        url="https://example.com/news/1",
        explicit_tickers=explicit,
    )


def test_official_company_code_has_highest_relevance() -> None:
    matcher = TickerMatcher({"2330": ("台積電",)})
    assert matcher.match(make_item("董事會決議", explicit=("2330",)))[0].relevance_score == 1.0


def test_alias_title_and_ticker_summary_are_explainable() -> None:
    matcher = TickerMatcher({"2330": ("台積電",), "2317": ("鴻海",)})
    matches = matcher.match(make_item("台積電法說會", "同時提及股票 2317。"))
    assert [(match.ticker, match.match_method) for match in matches] == [
        ("2317", "ticker_summary"),
        ("2330", "company_alias_title"),
    ]

