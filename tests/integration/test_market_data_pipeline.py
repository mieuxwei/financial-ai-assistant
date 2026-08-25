from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import MarketIngestionRun, MarketPrice
from backend.app.services.market_data import MarketDataIngestionService
from pipelines.market_data.errors import MarketDataQualityError
from pipelines.market_data.snapshot import build_market_snapshot
from pipelines.market_data.types import MarketBar, MarketDataRequest, ProviderFetchResult


class FixtureProvider:
    name = "fixture"

    def __init__(self, bars_by_ticker: dict[str, list[MarketBar]]) -> None:
        self.bars_by_ticker = bars_by_ticker

    def fetch_daily(self, request: MarketDataRequest) -> ProviderFetchResult:
        return ProviderFetchResult(request=request, bars=self.bars_by_ticker[request.ticker])


def make_bar(
    ticker: str,
    trading_date: date,
    *,
    close: str,
    high: str = "105",
    adjusted_close: str | None = None,
) -> MarketBar:
    close_value = Decimal(close)
    return MarketBar(
        ticker=ticker,
        trading_date=trading_date,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal("95"),
        close=close_value,
        adjusted_close=Decimal(adjusted_close) if adjusted_close else close_value,
        volume=1000,
        source="fixture",
    )


def make_request(ticker: str) -> MarketDataRequest:
    return MarketDataRequest(
        ticker=ticker,
        provider_symbol=f"{ticker}.TW",
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 25),
    )


def test_repeated_ingestion_upserts_without_duplicates_and_snapshot_is_stable(
    db_session: Session,
) -> None:
    request = make_request("2330")
    provider = FixtureProvider(
        {
            "2330": [
                make_bar("2330", date(2026, 8, 24), close="101"),
                make_bar("2330", date(2026, 8, 25), close="102"),
            ]
        }
    )
    service = MarketDataIngestionService(db_session, provider)

    first = service.ingest([request])
    first_snapshot = build_market_snapshot(
        db_session,
        tickers=["2330"],
        start_date=request.start_date,
        end_date=request.end_date,
        source="fixture",
    )
    second = service.ingest([request])
    second_snapshot = build_market_snapshot(
        db_session,
        tickers=["2330"],
        start_date=request.start_date,
        end_date=request.end_date,
        source="fixture",
    )

    row_count = db_session.scalar(select(func.count()).select_from(MarketPrice))
    assert first.records_upserted == second.records_upserted == 2
    assert row_count == 2
    assert first_snapshot["sha256"] == second_snapshot["sha256"]


def test_quality_failure_rolls_back_all_prices_and_records_failed_run(
    db_session: Session,
) -> None:
    requests = [make_request("0050"), make_request("2330")]
    provider = FixtureProvider(
        {
            "0050": [
                make_bar("0050", date(2026, 8, 24), close="101"),
                make_bar("0050", date(2026, 8, 25), close="102"),
            ],
            "2330": [make_bar("2330", date(2026, 8, 24), close="102", high="99")],
        }
    )

    with pytest.raises(MarketDataQualityError):
        MarketDataIngestionService(db_session, provider).ingest(requests)

    price_count = db_session.scalar(select(func.count()).select_from(MarketPrice))
    failed_run = db_session.scalar(
        select(MarketIngestionRun).where(MarketIngestionRun.status == "failed")
    )
    assert price_count == 0
    assert failed_run is not None
    assert failed_run.error_code == "MarketDataQualityError"
    assert set(failed_run.quality_report or {}) == {"0050", "2330"}


def test_adjusted_close_jitter_is_ignored_but_material_revision_is_applied(
    db_session: Session,
) -> None:
    request = make_request("2330")
    provider = FixtureProvider(
        {
            "2330": [
                make_bar(
                    "2330",
                    date(2026, 8, 24),
                    close="102",
                    adjusted_close="101.001",
                ),
                make_bar("2330", date(2026, 8, 25), close="103"),
            ]
        }
    )
    service = MarketDataIngestionService(db_session, provider)
    service.ingest([request])

    provider.bars_by_ticker["2330"][0] = make_bar(
        "2330",
        date(2026, 8, 24),
        close="102",
        adjusted_close="101.004",
    )
    service.ingest([request])
    row = db_session.get(
        MarketPrice,
        {"ticker": "2330", "trading_date": date(2026, 8, 24), "source": "fixture"},
    )
    assert row is not None
    assert row.adjusted_close == Decimal("101.001000")

    provider.bars_by_ticker["2330"][0] = make_bar(
        "2330",
        date(2026, 8, 24),
        close="102",
        adjusted_close="100.5",
    )
    service.ingest([request])
    db_session.refresh(row)
    assert row.adjusted_close == Decimal("100.500000")
