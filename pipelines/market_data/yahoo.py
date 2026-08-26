import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from datetime import time as datetime_time
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from pipelines.market_data.errors import ProviderResponseError, ProviderUnavailableError
from pipelines.market_data.types import MarketBar, MarketDataRequest, ProviderFetchResult

TAIPEI = ZoneInfo("Asia/Taipei")
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RAW_PRICE_QUANTUM = Decimal("0.000001")
ADJUSTED_PRICE_QUANTUM = Decimal("0.001")


class YahooFinanceProvider:
    """Small adapter around Yahoo's chart response, isolated behind a replaceable contract."""

    name = "yahoo"
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least one")
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "financial-ai-assistant/0.1 research"},
        )
        self.max_retries = max_retries
        self.sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "YahooFinanceProvider":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_daily(self, request: MarketDataRequest) -> ProviderFetchResult:
        response = self._request(request)
        try:
            payload = response.json()
            chart = payload["chart"]
            if chart.get("error"):
                raise ProviderResponseError("Yahoo returned a chart error")
            result = chart["result"][0]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderResponseError(
                "Yahoo response did not match the expected chart schema"
            ) from error
        return self._parse_result(request, result)

    def _request(self, request: MarketDataRequest) -> httpx.Response:
        url = f"{self.base_url}/{quote(request.provider_symbol, safe='')}"
        params = {
            "period1": self._epoch_at_taipei_midnight(request.start_date),
            "period2": self._epoch_at_taipei_midnight(request.end_date + timedelta(days=1)),
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url, params=params)
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response
                last_error = ProviderUnavailableError(
                    f"Yahoo temporarily unavailable with status {response.status_code}"
                )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = error
            except httpx.HTTPStatusError as error:
                raise ProviderResponseError(
                    f"Yahoo rejected the request with status {error.response.status_code}"
                ) from error
            if attempt < self.max_retries - 1:
                self.sleep(0.5 * (2**attempt))
        raise ProviderUnavailableError("Yahoo request failed after retries") from last_error

    def _parse_result(
        self,
        request: MarketDataRequest,
        result: dict[str, Any],
    ) -> ProviderFetchResult:
        try:
            timestamps = result.get("timestamp") or []
            indicators = result["indicators"]
            quote_values = indicators["quote"][0]
            adjusted_values = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderResponseError(
                "Yahoo indicators were missing from the response"
            ) from error

        bars: list[MarketBar] = []
        warnings: list[str] = []
        for index, timestamp in enumerate(timestamps):
            values = {
                "open": self._at(quote_values.get("open"), index),
                "high": self._at(quote_values.get("high"), index),
                "low": self._at(quote_values.get("low"), index),
                "close": self._at(quote_values.get("close"), index),
                "volume": self._at(quote_values.get("volume"), index),
            }
            if any(value is None for value in values.values()):
                warnings.append(f"skipped incomplete bar at timestamp index {index}")
                continue
            try:
                close = self._decimal(values["close"])
                adjusted_raw = self._at(adjusted_values, index)
                candidate = MarketBar(
                    ticker=request.ticker,
                    trading_date=(
                        datetime.fromtimestamp(timestamp, UTC).astimezone(TAIPEI).date()
                    ),
                    open=self._decimal(values["open"]),
                    high=self._decimal(values["high"]),
                    low=self._decimal(values["low"]),
                    close=close,
                    adjusted_close=(
                        self._decimal(adjusted_raw, ADJUSTED_PRICE_QUANTUM)
                        if adjusted_raw is not None
                        else close.quantize(ADJUSTED_PRICE_QUANTUM)
                    ),
                    volume=int(values["volume"]),
                    source=self.name,
                )
                if not self._is_structurally_valid(candidate):
                    warnings.append(
                        "skipped structurally invalid bar at timestamp index "
                        f"{index}"
                    )
                    continue
                bars.append(candidate)
            except (InvalidOperation, TypeError, ValueError) as error:
                warnings.append(
                    "skipped invalid numeric bar at timestamp index "
                    f"{index}: {type(error).__name__}"
                )
        return ProviderFetchResult(request=request, bars=bars, warnings=warnings)

    @staticmethod
    def _at(values: list[Any] | None, index: int) -> Any | None:
        if values is None or index >= len(values):
            return None
        return values[index]

    @staticmethod
    def _decimal(value: Any, quantum: Decimal = RAW_PRICE_QUANTUM) -> Decimal:
        return Decimal(str(value)).quantize(quantum)

    @staticmethod
    def _is_structurally_valid(bar: MarketBar) -> bool:
        prices = (bar.open, bar.high, bar.low, bar.close, bar.adjusted_close)
        return (
            min(prices) > 0
            and bar.high >= max(bar.open, bar.close)
            and bar.low <= min(bar.open, bar.close)
            and bar.high >= bar.low
            and bar.volume >= 0
        )

    @staticmethod
    def _epoch_at_taipei_midnight(value) -> int:
        local_value = datetime.combine(value, datetime_time.min, tzinfo=TAIPEI)
        return int(local_value.timestamp())
