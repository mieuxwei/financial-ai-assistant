import time
from collections.abc import Callable, Mapping

import httpx

from pipelines.news.errors import (
    NewsProviderResponseError,
    NewsProviderUnavailableError,
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retries(
    client: httpx.Client,
    url: str,
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
    params: Mapping[str, str | int | bool] | None = None,
    headers: Mapping[str, str] | None = None,
    backoff_seconds: tuple[float, ...] | None = None,
) -> httpx.Response:
    if max_retries < 1:
        raise ValueError("max_retries must be at least one")
    delays = (
        backoff_seconds
        if backoff_seconds is not None
        else tuple(0.5 * (2**attempt) for attempt in range(max_retries - 1))
    )
    if len(delays) != max_retries - 1:
        raise ValueError("backoff_seconds must have max_retries - 1 entries")
    if any(delay <= 0 for delay in delays):
        raise ValueError("backoff_seconds must be positive")
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.get(url, params=params, headers=headers)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response
            last_error = NewsProviderUnavailableError(
                f"news provider temporarily unavailable with status {response.status_code}"
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            last_error = error
        except httpx.HTTPStatusError as error:
            raise NewsProviderResponseError(
                f"news provider rejected the request with status {error.response.status_code}"
            ) from error
        if attempt < max_retries - 1:
            sleep(delays[attempt])
    raise NewsProviderUnavailableError("news request failed after retries") from last_error
