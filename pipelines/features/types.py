from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal

FEATURE_PIPELINE_VERSION = "features-v1"


@dataclass(frozen=True)
class FeatureConfig:
    tickers: tuple[str, ...]
    start_date: date
    end_date: date
    market_source: str
    sentiment_model_version: str | None = None
    benchmark_ticker: str | None = None
    market_timezone: str = "Asia/Taipei"
    market_close_time: time = time(13, 30)
    pipeline_version: str = FEATURE_PIPELINE_VERSION

    def __post_init__(self) -> None:
        normalized = tuple(sorted({ticker.strip().upper() for ticker in self.tickers}))
        if not normalized or any(not ticker for ticker in normalized):
            raise ValueError("at least one non-empty ticker is required")
        object.__setattr__(self, "tickers", normalized)
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if not self.market_source.strip():
            raise ValueError("market_source is required")
        if self.benchmark_ticker:
            object.__setattr__(self, "benchmark_ticker", self.benchmark_ticker.strip().upper())

    def to_dict(self) -> dict[str, object]:
        return {
            "tickers": list(self.tickers),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "market_source": self.market_source,
            "sentiment_model_version": self.sentiment_model_version,
            "benchmark_ticker": self.benchmark_ticker,
            "market_timezone": self.market_timezone,
            "market_close_time": self.market_close_time.isoformat(),
            "pipeline_version": self.pipeline_version,
        }


@dataclass(frozen=True)
class PriceObservation:
    ticker: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int


@dataclass(frozen=True)
class SentimentObservation:
    article_id: str
    ticker: str
    published_at: datetime
    source_type: str
    relevance_score: Decimal
    positive_prob: Decimal
    neutral_prob: Decimal
    negative_prob: Decimal
    sentiment_score: Decimal
    predicted_label: str


@dataclass(frozen=True)
class FeatureRow:
    ticker: str
    feature_date: date
    target_date: date
    information_cutoff: datetime
    latest_sentiment_published_at: datetime | None
    features: dict[str, float | int | None]
    forward_return_1d: float
    label_up: int

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["feature_date"] = self.feature_date.isoformat()
        payload["target_date"] = self.target_date.isoformat()
        payload["information_cutoff"] = self.information_cutoff.isoformat()
        payload["latest_sentiment_published_at"] = (
            self.latest_sentiment_published_at.isoformat()
            if self.latest_sentiment_published_at
            else None
        )
        return payload


@dataclass(frozen=True)
class FeatureDataset:
    config: FeatureConfig
    market_snapshot_sha256: str
    sentiment_snapshot_sha256: str
    rows: tuple[FeatureRow, ...]
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "modeling-dataset-v1",
            "config": self.config.to_dict(),
            "market_snapshot_sha256": self.market_snapshot_sha256,
            "sentiment_snapshot_sha256": self.sentiment_snapshot_sha256,
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
            "sha256": self.sha256,
        }
