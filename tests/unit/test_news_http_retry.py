import httpx
import pytest

from pipelines.news.http import get_with_retries


def test_retry_uses_frozen_source_backoff_values() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        status = 503 if attempts < 3 else 200
        return httpx.Response(status, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = get_with_retries(
            client,
            "https://example.test/source",
            max_retries=3,
            backoff_seconds=(1.0, 2.0),
            sleep=delays.append,
        )

    assert response.status_code == 200
    assert attempts == 3
    assert delays == [1.0, 2.0]


def test_retry_rejects_backoff_shape_that_does_not_match_attempts() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        with pytest.raises(ValueError, match="max_retries - 1"):
            get_with_retries(
                client,
                "https://example.test/source",
                max_retries=3,
                backoff_seconds=(1.0,),
            )
