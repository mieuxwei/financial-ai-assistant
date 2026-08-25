from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models import MarketIngestionRun
from backend.app.repositories.market_data import MarketDataRepository
from pipelines.market_data.base import MarketDataProvider
from pipelines.market_data.errors import MarketDataQualityError
from pipelines.market_data.quality import assess_market_data
from pipelines.market_data.types import MarketDataRequest


@dataclass(frozen=True)
class MarketIngestionResult:
    run_id: str
    status: str
    records_fetched: int
    records_upserted: int
    quality_report: dict[str, object]


class MarketDataIngestionService:
    def __init__(self, session: Session, provider: MarketDataProvider) -> None:
        self.session = session
        self.provider = provider
        self.repository = MarketDataRepository(session)

    def ingest(self, requests: list[MarketDataRequest]) -> MarketIngestionResult:
        if not requests:
            raise ValueError("at least one market-data request is required")
        self._validate_shared_range(requests)
        run = MarketIngestionRun(
            provider=self.provider.name,
            tickers=[
                {"ticker": request.ticker, "provider_symbol": request.provider_symbol}
                for request in requests
            ],
            start_date=requests[0].start_date,
            end_date=requests[0].end_date,
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        try:
            all_bars = []
            reports: dict[str, object] = {}
            for request in requests:
                fetched = self.provider.fetch_daily(request)
                report = assess_market_data(request, fetched.bars, fetched.warnings)
                reports[request.ticker] = report.to_dict()
                if not report.passed:
                    raise MarketDataQualityError(
                        f"quality checks failed for ticker {request.ticker}"
                    )
                all_bars.extend(fetched.bars)

            ingested_at = datetime.now(UTC)
            upserted = self.repository.upsert_bars(all_bars, ingested_at)
            run.status = "succeeded"
            run.records_fetched = len(all_bars)
            run.records_upserted = upserted
            run.quality_report = reports
            run.completed_at = ingested_at
            self.session.commit()
            return MarketIngestionResult(
                run_id=run.id,
                status=run.status,
                records_fetched=run.records_fetched,
                records_upserted=run.records_upserted,
                quality_report=reports,
            )
        except Exception as error:
            self.session.rollback()
            failed_run = self.session.get(MarketIngestionRun, run_id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.records_fetched = len(all_bars)
                failed_run.quality_report = reports
                failed_run.error_code = type(error).__name__
                failed_run.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    @staticmethod
    def _validate_shared_range(requests: list[MarketDataRequest]) -> None:
        expected = (requests[0].start_date, requests[0].end_date)
        if any((request.start_date, request.end_date) != expected for request in requests):
            raise ValueError("all requests in one ingestion run must use the same date range")
