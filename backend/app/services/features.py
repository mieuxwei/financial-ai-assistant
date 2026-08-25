from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.models import DailyFeature, FeatureDatasetRun
from backend.app.repositories.features import FeatureRepository
from pipelines.features.builder import build_modeling_dataset
from pipelines.features.types import (
    FeatureConfig,
    FeatureDataset,
    PriceObservation,
    SentimentObservation,
)


@dataclass(frozen=True)
class FeatureBuildResult:
    dataset_run_id: str
    status: str
    row_count: int
    dataset_sha256: str
    reused: bool
    dataset: FeatureDataset


class FeatureDatasetService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = FeatureRepository(session)

    def build(self, config: FeatureConfig) -> FeatureBuildResult:
        query_tickers = list(config.tickers)
        if config.benchmark_ticker and config.benchmark_ticker not in query_tickers:
            query_tickers.append(config.benchmark_ticker)
        price_rows = self.repository.list_prices(
            tickers=query_tickers,
            start_date=config.start_date,
            end_date=config.end_date,
            source=config.market_source,
        )
        sentiment_rows = []
        if config.sentiment_model_version:
            timezone = ZoneInfo(config.market_timezone)
            start = datetime.combine(config.start_date, time.min, tzinfo=timezone)
            end = datetime.combine(config.end_date + timedelta(days=1), time.min, tzinfo=timezone)
            sentiment_rows = self.repository.list_sentiment(
                tickers=list(config.tickers),
                start=start,
                end=end,
                model_version=config.sentiment_model_version,
            )
        dataset = build_modeling_dataset(
            [_price_observation(row) for row in price_rows],
            [_sentiment_observation(*row) for row in sentiment_rows],
            config,
        )
        if not dataset.rows:
            raise ValueError(
                "no modeling rows were produced; each ticker needs at least 27 ordered prices"
            )
        existing = self.repository.find_run_by_hash(dataset.sha256)
        if existing is not None:
            return FeatureBuildResult(
                dataset_run_id=existing.id,
                status=existing.status,
                row_count=existing.row_count,
                dataset_sha256=existing.dataset_sha256,
                reused=True,
                dataset=dataset,
            )

        config_payload = config.to_dict()
        run = FeatureDatasetRun(
            pipeline_version=config.pipeline_version,
            config_sha256=_hash(config_payload),
            market_snapshot_sha256=dataset.market_snapshot_sha256,
            sentiment_snapshot_sha256=dataset.sentiment_snapshot_sha256,
            dataset_sha256=dataset.sha256,
            market_source=config.market_source,
            sentiment_model_version=config.sentiment_model_version,
            start_date=config.start_date,
            end_date=config.end_date,
            row_count=len(dataset.rows),
            config=config_payload,
            status="succeeded",
        )
        stored_rows = [
            DailyFeature(
                dataset_run_id="",
                ticker=row.ticker,
                feature_date=row.feature_date,
                target_date=row.target_date,
                information_cutoff=row.information_cutoff,
                latest_sentiment_published_at=row.latest_sentiment_published_at,
                features=row.features,
                forward_return_1d=Decimal(str(row.forward_return_1d)),
                label_up=row.label_up,
            )
            for row in dataset.rows
        ]
        self.repository.add_dataset(run, stored_rows)
        self.session.commit()
        return FeatureBuildResult(
            dataset_run_id=run.id,
            status=run.status,
            row_count=run.row_count,
            dataset_sha256=run.dataset_sha256,
            reused=False,
            dataset=dataset,
        )


def _price_observation(row: object) -> PriceObservation:
    return PriceObservation(
        ticker=row.ticker,
        trading_date=row.trading_date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        adjusted_close=row.adjusted_close,
        volume=row.volume,
    )


def _sentiment_observation(result: object, article: object, link: object) -> SentimentObservation:
    published_at = article.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    return SentimentObservation(
        article_id=article.id,
        ticker=result.ticker,
        published_at=published_at,
        source_type=article.source_type,
        relevance_score=link.relevance_score,
        positive_prob=result.positive_prob,
        neutral_prob=result.neutral_prob,
        negative_prob=result.negative_prob,
        sentiment_score=result.sentiment_score,
        predicted_label=result.predicted_label,
    )


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
