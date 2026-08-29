from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field

from pipelines.news.errors import NewsProviderResponseError
from pipelines.news.http import get_with_retries
from research.training.fsc_corpus import normalize_text

TAIPEI = ZoneInfo("Asia/Taipei")
SOURCE_ID = "twmd_major_events"
SCHEMA_VERSION = "b2.1-twmd-event-metadata-v1"
FILTER_CONTRACT_VERSION = "twmd-runtime-filter-contract-v1"
TIMESTAMP_SEMANTICS = (
    "MOPS-derived disclosure date and second-resolution local clock; Asia/Taipei is a frozen "
    "source-contract assumption because the API returns no UTC offset"
)


@dataclass(frozen=True)
class TwmdMajorEvent:
    event_id: str
    ticker: str
    market: str
    event_date: date
    event_time: str
    publication_timestamp: datetime
    subject: str
    event_class: str
    confidence: float
    rule_version: str


@dataclass(frozen=True)
class TwmdEventBatch:
    events: tuple[TwmdMajorEvent, ...]
    response_sha256: str
    duplicate_count: int
    known_gaps: tuple[str, ...]
    warnings: tuple[str, ...]
    filter_contract_version: str = FILTER_CONTRACT_VERSION


class B21TwmdDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["b2.1-twmd-event-metadata-v1"] = SCHEMA_VERSION
    document_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    document_version_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_id: Literal["twmd_major_events"] = SOURCE_ID
    source_type: Literal["LICENSED_EVENT_METADATA"] = "LICENSED_EVENT_METADATA"
    ticker: str
    market: str
    publication_timestamp: datetime
    timezone: Literal["Asia/Taipei"] = "Asia/Taipei"
    timestamp_semantics: Literal[
        "MOPS-derived disclosure date and second-resolution local clock; Asia/Taipei is a frozen "
        "source-contract assumption because the API returns no UTC offset"
    ] = TIMESTAMP_SEMANTICS
    timezone_basis: Literal["SOURCE_CONTRACT_ASSUMPTION_NO_OFFSET_IN_API"] = (
        "SOURCE_CONTRACT_ASSUMPTION_NO_OFFSET_IN_API"
    )
    subject_title: str
    event_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    rule_version: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_payload_ref: str
    rights_tier: Literal["LICENSED_EVENT_METADATA_PRIVATE"] = (
        "LICENSED_EVENT_METADATA_PRIVATE"
    )
    public_demo_text_allowed: Literal[False] = False
    full_text_available: Literal[False] = False
    sentiment_ground_truth: Literal[False] = False
    human_validated: Literal[False] = False
    lineage: dict[str, str]


class TwmdMajorEventProvider:
    name = SOURCE_ID
    endpoint = "https://api.twmarketdata.com/v2/datasets/major-event-taxonomy"

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        max_window_days: int = 31,
        max_limit: int = 100,
        max_response_bytes: int = 1_000_000,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        credential = api_key.strip()
        if not credential or "\n" in credential or "\r" in credential:
            raise ValueError("a single-line TWMD API credential is required")
        self._api_key = credential
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "financial-ai-assistant/0.1 b2.1-twmd"},
        )
        self.max_retries = max_retries
        self.max_window_days = max_window_days
        self.max_limit = max_limit
        self.max_response_bytes = max_response_bytes
        self.sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> TwmdMajorEventProvider:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch(
        self,
        *,
        ticker: str,
        date_from: date,
        date_to: date,
        limit: int = 100,
    ) -> TwmdEventBatch:
        self._validate_request(ticker=ticker, date_from=date_from, date_to=date_to, limit=limit)
        params: dict[str, str | int] = {
            "ticker": ticker,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "limit": limit,
        }
        response = get_with_retries(
            self.client,
            self.endpoint,
            max_retries=self.max_retries,
            sleep=self.sleep,
            params=params,
            headers={"X-API-Key": self._api_key},
        )
        if len(response.content) > self.max_response_bytes:
            raise NewsProviderResponseError("TWMD response exceeded the B2.1 size limit")
        try:
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise TypeError
            self._validate_filter_echo(payload, params)
            rows = payload["data"]
            if len(rows) >= limit:
                raise NewsProviderResponseError(
                    "TWMD response reached the row limit; split the date window before ingestion"
                )
            parsed = [
                self._parse(
                    row,
                    ticker=ticker,
                    date_from=date_from,
                    date_to=date_to,
                )
                for row in rows
            ]
            unique = {event.event_id: event for event in parsed}
            gaps = payload.get("known_gaps", [])
            warnings = payload.get("warnings", [])
            if not isinstance(gaps, list) or not isinstance(warnings, list):
                raise TypeError
        except NewsProviderResponseError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise NewsProviderResponseError(
                "TWMD major-event response did not match the frozen B2.1 contract"
            ) from error
        return TwmdEventBatch(
            events=tuple(unique.values()),
            response_sha256=hashlib.sha256(response.content).hexdigest(),
            duplicate_count=len(parsed) - len(unique),
            known_gaps=tuple(str(item) for item in gaps),
            warnings=tuple(str(item) for item in warnings),
        )

    def _validate_request(
        self,
        *,
        ticker: str,
        date_from: date,
        date_to: date,
        limit: int,
    ) -> None:
        if not re.fullmatch(r"[0-9A-Z]{2,12}", ticker):
            raise ValueError("ticker must be an explicit Taiwan security code")
        if date_to < date_from:
            raise ValueError("date_to must not precede date_from")
        if (date_to - date_from).days + 1 > self.max_window_days:
            raise ValueError("TWMD request exceeds the frozen date-window limit")
        if not 1 <= limit <= self.max_limit:
            raise ValueError("TWMD request exceeds the frozen row limit")

    @staticmethod
    def _validate_filter_echo(payload: dict[str, object], expected: dict[str, str | int]) -> None:
        context = payload.get("request_context")
        filters = context.get("filters") if isinstance(context, dict) else None
        if not isinstance(filters, dict):
            raise NewsProviderResponseError("TWMD response omitted the runtime filter echo")
        for name, expected_value in expected.items():
            if filters.get(name) != expected_value:
                raise NewsProviderResponseError(
                    f"TWMD response did not apply the requested {name} filter"
                )

    @staticmethod
    def _parse(
        raw: object,
        *,
        ticker: str,
        date_from: date,
        date_to: date,
    ) -> TwmdMajorEvent:
        if not isinstance(raw, dict):
            raise TypeError("event must be an object")
        required = {
            "ticker",
            "market",
            "event_date",
            "event_time",
            "subject",
            "event_class",
            "confidence",
            "rule_version",
        }
        if not required <= set(raw):
            raise KeyError("required TWMD fields are missing")
        row_ticker = str(raw["ticker"]).strip()
        if row_ticker != ticker:
            raise ValueError("TWMD returned a different ticker")
        event_date = date.fromisoformat(str(raw["event_date"]))
        if not date_from <= event_date <= date_to:
            raise ValueError("TWMD returned an event outside the requested date window")
        event_time = str(raw["event_time"]).strip()
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d", event_time):
            raise ValueError("TWMD event_time must have HH:MM:SS precision")
        subject = normalize_text(str(raw["subject"]))
        event_class = normalize_text(str(raw["event_class"]))
        rule_version = str(raw["rule_version"]).strip()
        if not subject or not event_class or not rule_version:
            raise ValueError("TWMD subject, event class and rule version are required")
        confidence = float(raw["confidence"])
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("TWMD confidence must be between zero and one")
        published_at = datetime.fromisoformat(f"{event_date.isoformat()}T{event_time}").replace(
            tzinfo=TAIPEI
        )
        identity = "\x1f".join(
            (row_ticker, event_date.isoformat(), event_time, subject, rule_version)
        )
        return TwmdMajorEvent(
            event_id=hashlib.sha256(identity.encode()).hexdigest(),
            ticker=row_ticker,
            market=str(raw["market"]).strip(),
            event_date=event_date,
            event_time=event_time,
            publication_timestamp=published_at,
            subject=subject,
            event_class=event_class,
            confidence=confidence,
            rule_version=rule_version,
        )


def normalize_twmd_event(
    event: TwmdMajorEvent,
    *,
    response_sha256: str,
    raw_payload_ref: str,
) -> B21TwmdDocument:
    content_basis = json.dumps(
        {
            "subject": event.subject,
            "event_class": event.event_class,
            "confidence": event.confidence,
            "rule_version": event.rule_version,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    content_hash = hashlib.sha256(content_basis.encode()).hexdigest()
    version_id = hashlib.sha256(f"{event.event_id}\x1f{content_hash}".encode()).hexdigest()
    return B21TwmdDocument(
        document_id=event.event_id,
        document_version_id=version_id,
        ticker=event.ticker,
        market=event.market,
        publication_timestamp=event.publication_timestamp,
        subject_title=event.subject,
        event_class=event.event_class,
        confidence=event.confidence,
        rule_version=event.rule_version,
        content_hash=content_hash,
        response_sha256=response_sha256,
        raw_payload_ref=raw_payload_ref,
        lineage={
            "provider": "TWMD",
            "dataset": "major_event_taxonomy",
            "filter_contract_version": FILTER_CONTRACT_VERSION,
            "rule_version": event.rule_version,
        },
    )
