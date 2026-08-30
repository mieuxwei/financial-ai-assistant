import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from pipelines.news.errors import NewsProviderResponseError
from pipelines.news.http import get_with_retries
from pipelines.news.types import NewsItem, NewsProviderBatch, NewsProviderPayload

TAIPEI = ZoneInfo("Asia/Taipei")


class TwseMaterialAnnouncementProvider:
    name = "twse_material"
    source_type = "official_announcement"
    endpoint = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        backoff_seconds: tuple[float, ...] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "financial-ai-assistant/0.1 research"},
        )
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "TwseMaterialAnnouncementProvider":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch(self) -> list[NewsItem]:
        return list(self.fetch_batch().items)

    def fetch_batch(self) -> NewsProviderBatch:
        payload = self.fetch_raw()
        return NewsProviderBatch(
            raw_payload=payload.raw_payload,
            content_type=payload.content_type,
            items=self.parse_raw(payload),
        )

    def fetch_raw(self) -> NewsProviderPayload:
        response = get_with_retries(
            self.client,
            self.endpoint,
            max_retries=self.max_retries,
            sleep=self.sleep,
            backoff_seconds=self.backoff_seconds,
        )
        return NewsProviderPayload(
            raw_payload=response.content,
            content_type=response.headers.get("content-type", "application/json"),
        )

    def parse_raw(self, payload: NewsProviderPayload) -> tuple[NewsItem, ...]:
        try:
            decoded = json.loads(payload.raw_payload)
            if not isinstance(decoded, list):
                raise TypeError
            return tuple(self._parse(row) for row in decoded)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise NewsProviderResponseError(
                "TWSE material-announcement response did not match the expected schema"
            ) from error

    def _parse(self, raw: object) -> NewsItem:
        if not isinstance(raw, dict):
            raise TypeError("announcement must be an object")
        row = {str(key).strip(): value for key, value in raw.items()}
        title = str(row["主旨"]).strip()
        ticker = str(row["公司代號"]).strip()
        company_name = str(row["公司名稱"]).strip()
        published_at = _parse_roc_datetime(str(row["發言日期"]), str(row["發言時間"]))
        external_identity = "|".join((ticker, published_at.isoformat(), title))
        external_id = hashlib.sha256(external_identity.encode()).hexdigest()
        explanation = _short_text(row.get("說明"))
        return NewsItem(
            title=title,
            published_at=published_at,
            source=self.name,
            source_type=self.source_type,
            url=self.endpoint,
            summary=explanation,
            external_id=external_id,
            explicit_tickers=(ticker,),
            metadata={
                "company_name": company_name,
                "clause": str(row.get("符合條款", "")).strip(),
                "fact_date": str(row.get("事實發生日", "")).strip(),
            },
        )


def _parse_roc_datetime(date_value: str, time_value: str) -> datetime:
    compact_date = date_value.strip()
    if len(compact_date) != 7 or not compact_date.isdigit():
        raise ValueError("invalid ROC date")
    compact_time = time_value.strip().zfill(6)
    if len(compact_time) != 6 or not compact_time.isdigit():
        raise ValueError("invalid announcement time")
    return datetime(
        int(compact_date[:3]) + 1911,
        int(compact_date[3:5]),
        int(compact_date[5:7]),
        int(compact_time[:2]),
        int(compact_time[2:4]),
        int(compact_time[4:6]),
        tzinfo=TAIPEI,
    )


def _short_text(value: object, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").split())
    return text[:limit] or None
