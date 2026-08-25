from typing import Protocol

from pipelines.news.types import NewsItem


class NewsProvider(Protocol):
    name: str

    def fetch(self) -> list[NewsItem]: ...

