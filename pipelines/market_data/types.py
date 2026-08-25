from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from backend.app.services.tickers import normalize_ticker


@dataclass(frozen=True)
class MarketDataRequest:
    ticker: str
    provider_symbol: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", normalize_ticker(self.ticker))
        normalized_symbol = self.provider_symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("provider symbol is required")
        object.__setattr__(self, "provider_symbol", normalized_symbol)
        if self.end_date < self.start_date:
            raise ValueError("end date must not be before start date")


@dataclass(frozen=True)
class MarketBar:
    ticker: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", normalize_ticker(self.ticker))
        if not self.source.strip():
            raise ValueError("market-data source is required")


@dataclass(frozen=True)
class ProviderFetchResult:
    request: MarketDataRequest
    bars: list[MarketBar]
    warnings: list[str] = field(default_factory=list)
