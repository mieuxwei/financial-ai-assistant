from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import MarketPrice
from pipelines.market_data.types import MarketBar

ADJUSTED_CLOSE_JITTER_TOLERANCE = Decimal("0.005")
RAW_CLOSE_JITTER_TOLERANCE = Decimal("0.000001")


class MarketDataRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_bars(self, bars: list[MarketBar], ingested_at: datetime) -> int:
        for bar in bars:
            identity = {
                "ticker": bar.ticker,
                "trading_date": bar.trading_date,
                "source": bar.source,
            }
            row = self.session.get(MarketPrice, identity)
            if row is None:
                row = MarketPrice(**identity)
                self.session.add(row)
                adjusted_close = bar.adjusted_close
            elif (
                abs(row.adjusted_close - bar.adjusted_close)
                <= ADJUSTED_CLOSE_JITTER_TOLERANCE
                and abs(row.close - bar.close) <= RAW_CLOSE_JITTER_TOLERANCE
            ):
                adjusted_close = row.adjusted_close
            else:
                adjusted_close = bar.adjusted_close
            row.open = bar.open
            row.high = bar.high
            row.low = bar.low
            row.close = bar.close
            row.adjusted_close = adjusted_close
            row.volume = bar.volume
            row.ingested_at = ingested_at
        return len(bars)

    def list_bars(
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
