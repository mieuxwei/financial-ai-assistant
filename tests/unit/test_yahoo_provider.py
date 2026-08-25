from datetime import UTC, date, datetime

import httpx

from pipelines.market_data.types import MarketDataRequest
from pipelines.market_data.yahoo import YahooFinanceProvider


def yahoo_payload() -> dict[str, object]:
    timestamp = int(datetime(2026, 8, 24, 5, 30, tzinfo=UTC).timestamp())
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [timestamp],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0],
                                "high": [105.0],
                                "low": [99.0],
                                "close": [103.0],
                                "volume": [123456],
                            }
                        ],
                        "adjclose": [{"adjclose": [102.5]}],
                    },
                }
            ],
        }
    }


def request() -> MarketDataRequest:
    return MarketDataRequest(
        ticker="2330",
        provider_symbol="2330.TW",
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 24),
    )


def test_yahoo_provider_parses_daily_ohlcv() -> None:
    transport = httpx.MockTransport(lambda incoming: httpx.Response(200, json=yahoo_payload()))
    client = httpx.Client(transport=transport)
    provider = YahooFinanceProvider(client=client)

    result = provider.fetch_daily(request())

    assert result.warnings == []
    assert len(result.bars) == 1
    bar = result.bars[0]
    assert bar.trading_date == date(2026, 8, 24)
    assert bar.adjusted_close.as_tuple().exponent == -3
    assert bar.adjusted_close == 102.5
    assert bar.volume == 123456
    client.close()


def test_yahoo_provider_retries_transient_status() -> None:
    attempts = 0
    sleeps: list[float] = []

    def handler(incoming: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=yahoo_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = YahooFinanceProvider(client=client, sleep=sleeps.append)

    result = provider.fetch_daily(request())

    assert len(result.bars) == 1
    assert attempts == 2
    assert sleeps == [0.5]
    client.close()
