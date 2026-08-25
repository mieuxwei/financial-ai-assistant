import html
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import httpx

from pipelines.news.errors import NewsProviderResponseError
from pipelines.news.http import get_with_retries
from pipelines.news.types import NewsItem

CONTENT_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"
DC_DATE_TAG = "{http://purl.org/dc/elements/1.1/}date"


class TwseNewsRssProvider:
    name = "twse_news_rss"
    source_type = "official_rss"
    endpoint = "https://www.twse.com.tw/rwd/zh/news/feed?type=rss"
    base_url = "https://www.twse.com.tw"

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

    def __enter__(self) -> "TwseNewsRssProvider":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch(self) -> list[NewsItem]:
        response = get_with_retries(
            self.client, self.endpoint, max_retries=self.max_retries, sleep=self.sleep
        )
        try:
            root = ET.fromstring(response.content)
            return [self._parse(item) for item in root.findall("./channel/item")]
        except (ET.ParseError, TypeError, ValueError) as error:
            raise NewsProviderResponseError(
                "TWSE RSS response did not match the expected schema"
            ) from error

    def _parse(self, item: ET.Element) -> NewsItem:
        title = _required_text(item, "title")
        relative_url = _required_text(item, "link")
        date_text = item.findtext(DC_DATE_TAG) or item.findtext("pubDate")
        if not date_text:
            raise ValueError("RSS item is missing publication time")
        try:
            published_at = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        except ValueError:
            published_at = parsedate_to_datetime(date_text)
        raw_content = item.findtext(CONTENT_TAG)
        return NewsItem(
            title=title,
            published_at=published_at,
            source=self.name,
            source_type=self.source_type,
            url=urljoin(self.base_url, relative_url),
            summary=_short_html_excerpt(raw_content),
            external_id=(item.findtext("guid") or relative_url).strip(),
        )


def _required_text(item: ET.Element, tag: str) -> str:
    value = item.findtext(tag)
    if not value or not value.strip():
        raise ValueError(f"RSS item is missing {tag}")
    return value.strip()


def _short_html_excerpt(value: str | None, limit: int = 500) -> str | None:
    if not value:
        return None
    without_tags = re.sub(r"<[^>]+>", " ", value)
    text = " ".join(html.unescape(without_tags).split())
    return text[:limit] or None
