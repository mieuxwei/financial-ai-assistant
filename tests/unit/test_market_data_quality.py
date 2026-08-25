from datetime import date
from decimal import Decimal

from pipelines.market_data.quality import assess_market_data
from pipelines.market_data.types import MarketBar, MarketDataRequest


def bar(trading_date: date, *, high: str = "105", low: str = "95") -> MarketBar:
    return MarketBar(
        ticker="2330",
        trading_date=trading_date,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("102"),
        adjusted_close=Decimal("102"),
        volume=1000,
        source="fixture",
    )


def test_quality_report_marks_weekday_gaps_as_warnings() -> None:
    request = MarketDataRequest(
        ticker="2330",
        provider_symbol="2330.TW",
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 26),
    )

    report = assess_market_data(
        request,
        [bar(date(2026, 8, 24)), bar(date(2026, 8, 26))],
    )

    assert report.passed is True
    assert report.potential_missing_weekdays == ["2026-08-25"]
    assert "exchange-calendar" in report.warnings[0]


def test_quality_report_rejects_invalid_ohlc() -> None:
    request = MarketDataRequest(
        ticker="2330",
        provider_symbol="2330.TW",
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 24),
    )

    report = assess_market_data(request, [bar(date(2026, 8, 24), high="99")])

    assert report.passed is False
    assert report.fatal_issues == ["invalid OHLC range on 2026-08-24"]
