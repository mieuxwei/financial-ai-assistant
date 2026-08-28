import csv
import hashlib
import io
import time
from collections.abc import Callable

import httpx

from pipelines.news.errors import NewsProviderResponseError
from pipelines.news.http import get_with_retries
from pipelines.news.twse_material import _parse_roc_datetime, _short_text
from pipelines.news.types import NewsItem


class TpexMaterialAnnouncementProvider:
    name = "tpex_openapi_daily_material"
    source_type = "official_announcement"
    endpoint = "https://mopsfin.twse.com.tw/opendata/t187ap04_O.csv"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
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

    def __enter__(self) -> "TpexMaterialAnnouncementProvider":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch(self) -> list[NewsItem]:
        response = get_with_retries(
            self.client, self.endpoint, max_retries=self.max_retries, sleep=self.sleep
        )
        try:
            text = response.content.decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))
            if not rows:
                return []
            return [self._parse(row) for row in rows]
        except (KeyError, TypeError, UnicodeDecodeError, ValueError) as error:
            raise NewsProviderResponseError(
                "TPEx material-announcement response did not match the expected schema"
            ) from error

    def _parse(self, raw: dict[str, str]) -> NewsItem:
        row = {str(key).strip(): value for key, value in raw.items()}
        title = str(row["主旨"]).strip()
        ticker = str(row["公司代號"]).strip()
        company_name = str(row["公司名稱"]).strip()
        published_at = _parse_roc_datetime(str(row["發言日期"]), str(row["發言時間"]))
        external_identity = "|".join((ticker, published_at.isoformat(), title))
        external_id = hashlib.sha256(external_identity.encode()).hexdigest()
        return NewsItem(
            title=title,
            published_at=published_at,
            source=self.name,
            source_type=self.source_type,
            url=self.endpoint,
            summary=_short_text(row.get("說明")),
            external_id=external_id,
            explicit_tickers=(ticker,),
            metadata={
                "company_name": company_name,
                "clause": str(row.get("符合條款", "")).strip(),
                "fact_date": str(row.get("事實發生日", "")).strip(),
            },
        )
