import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from pipelines.news.errors import NewsProviderResponseError
from pipelines.news.twmd_major_events import (
    TwmdMajorEventProvider,
    normalize_twmd_event,
)


def _payload(*, ticker: str = "2330", event_date: str = "2024-01-15") -> dict[str, object]:
    row = {
        "ticker": ticker,
        "market": "TWSE",
        "event_date": event_date,
        "event_time": "18:01:02",
        "subject": " 董事會   重大決議 ",
        "event_class": "其他",
        "confidence": 0.8,
        "rule_version": "mops_taxonomy_v1",
    }
    return {
        "data": [row],
        "data_count": 1,
        "request_context": {
            "filters": {
                "ticker": "2330",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "limit": 2,
            }
        },
        "known_gaps": ["event_class_is_inferred"],
        "warnings": ["not_investment_advice"],
    }


def _provider(payload: dict[str, object]) -> TwmdMajorEventProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "example"
        assert request.url.params["ticker"] == "2330"
        assert request.url.params["date_from"] == "2024-01-01"
        assert request.url.params["date_to"] == "2024-01-31"
        assert "symbol" not in request.url.params
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return TwmdMajorEventProvider(api_key="example", client=client, max_retries=1)


def test_provider_enforces_runtime_filters_timezone_and_schema() -> None:
    batch = _provider(_payload()).fetch(
        ticker="2330",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
        limit=2,
    )
    event = batch.events[0]
    assert event.subject == "董事會 重大決議"
    assert event.publication_timestamp.isoformat() == "2024-01-15T18:01:02+08:00"
    assert event.confidence == 0.8
    assert batch.duplicate_count == 0
    assert len(batch.response_sha256) == 64


def test_provider_fails_closed_when_filter_echo_mismatches() -> None:
    payload = _payload()
    payload["request_context"]["filters"]["ticker"] = None  # type: ignore[index]
    with pytest.raises(NewsProviderResponseError, match="ticker filter"):
        _provider(payload).fetch(
            ticker="2330",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            limit=2,
        )


def test_provider_rejects_out_of_window_rows_and_oversized_requests() -> None:
    with pytest.raises(NewsProviderResponseError, match="frozen B2.1 contract"):
        _provider(_payload(event_date="2024-02-01")).fetch(
            ticker="2330",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            limit=2,
        )
    with pytest.raises(ValueError, match="date-window"):
        _provider(_payload()).fetch(
            ticker="2330",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 2, 1),
            limit=2,
        )


def test_provider_rejects_limit_reached_instead_of_silently_truncating() -> None:
    payload = _payload()
    payload["data"] = [payload["data"][0], payload["data"][0]]  # type: ignore[index]
    with pytest.raises(NewsProviderResponseError, match="reached the row limit"):
        _provider(payload).fetch(
            ticker="2330",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            limit=2,
        )


def test_exact_duplicates_are_deduplicated_and_normalized_as_licensed_metadata() -> None:
    payload = _payload()
    payload["data"] = [payload["data"][0], payload["data"][0]]  # type: ignore[index]
    payload["request_context"]["filters"]["limit"] = 3  # type: ignore[index]
    batch = _provider_with_limit(payload, limit=3).fetch(
        ticker="2330",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
        limit=3,
    )
    assert len(batch.events) == 1
    assert batch.duplicate_count == 1
    document = normalize_twmd_event(
        batch.events[0],
        response_sha256=batch.response_sha256,
        raw_payload_ref="private/raw/twmd/test.json",
    )
    assert document.source_type == "LICENSED_EVENT_METADATA"
    assert document.rights_tier == "LICENSED_EVENT_METADATA_PRIVATE"
    assert document.public_demo_text_allowed is False
    assert document.full_text_available is False
    assert document.sentiment_ground_truth is False
    assert document.human_validated is False
    unsafe = document.model_dump(mode="json")
    unsafe["sentiment_ground_truth"] = True
    with pytest.raises(ValidationError):
        type(document).model_validate(unsafe)


def _provider_with_limit(payload: dict[str, object], *, limit: int) -> TwmdMajorEventProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == str(limit)
        return httpx.Response(200, json=payload)

    return TwmdMajorEventProvider(
        api_key="example",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=1,
    )


def test_b21_contract_keeps_b2_v1_immutable_and_b3_stopped() -> None:
    contract = json.loads(
        Path("research/configs/b2_1_twmd_secondary_source.v1.json").read_text(encoding="utf-8")
    )
    assert contract["status"] == "ACCEPT_SECONDARY_CONTRACT_READY_NO_DATASET_INGESTION"
    assert contract["runtime_query_fields"] == ["ticker", "date_from", "date_to", "limit"]
    assert contract["require_filter_echo"] is True
    assert contract["reject_when_limit_reached"] is True
    assert contract["b2_v1_unchanged"] is True
    assert contract["b3_started"] is False
