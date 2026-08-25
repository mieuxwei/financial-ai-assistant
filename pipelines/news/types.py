from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    title: str
    published_at: datetime
    source: str
    source_type: str
    url: str
    summary: str | None = None
    language: str = "zh-TW"
    external_id: str | None = None
    explicit_tickers: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("news title is required")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must include a timezone")
        if not self.source.strip() or not self.url.strip():
            raise ValueError("news source and URL are required")


@dataclass(frozen=True)
class TickerMatch:
    ticker: str
    relevance_score: float
    match_method: str

