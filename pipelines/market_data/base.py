from typing import Protocol

from pipelines.market_data.types import MarketDataRequest, ProviderFetchResult


class MarketDataProvider(Protocol):
    name: str

    def fetch_daily(self, request: MarketDataRequest) -> ProviderFetchResult: ...
