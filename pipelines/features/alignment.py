from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pipelines.features.types import FeatureConfig, SentimentObservation


def information_cutoff(feature_date: date, config: FeatureConfig) -> datetime:
    local = datetime.combine(
        feature_date,
        config.market_close_time,
        tzinfo=ZoneInfo(config.market_timezone),
    )
    return local.astimezone(UTC)


def assign_sentiment_to_sessions(
    events: list[SentimentObservation],
    trading_dates_by_ticker: dict[str, list[date]],
    config: FeatureConfig,
) -> dict[tuple[str, date], list[SentimentObservation]]:
    assigned: dict[tuple[str, date], list[SentimentObservation]] = defaultdict(list)
    timezone = ZoneInfo(config.market_timezone)
    for event in sorted(events, key=lambda item: (item.published_at, item.article_id, item.ticker)):
        dates = trading_dates_by_ticker.get(event.ticker, [])
        if not dates:
            continue
        published_at = event.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        local = published_at.astimezone(timezone)
        candidate = local.date()
        index = bisect_left(dates, candidate)
        if index >= len(dates):
            continue
        session_date = dates[index]
        if (
            session_date == candidate
            and local.timetz().replace(tzinfo=None) > config.market_close_time
        ):
            index += 1
            if index >= len(dates):
                continue
            session_date = dates[index]
        assigned[(event.ticker, session_date)].append(event)
    return dict(assigned)
