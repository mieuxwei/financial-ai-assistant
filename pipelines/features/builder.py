from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime

from pipelines.features.alignment import assign_sentiment_to_sessions, information_cutoff
from pipelines.features.technical import (
    historical_volatility,
    macd_series,
    moving_average_deviation,
    pct_change,
    rolling_zscore,
    rsi,
)
from pipelines.features.types import (
    FeatureConfig,
    FeatureDataset,
    FeatureRow,
    PriceObservation,
    SentimentObservation,
)


def build_modeling_dataset(
    prices: list[PriceObservation],
    sentiment: list[SentimentObservation],
    config: FeatureConfig,
) -> FeatureDataset:
    price_groups = _group_prices(prices, config)
    trading_dates = {
        ticker: [row.trading_date for row in rows] for ticker, rows in price_groups.items()
    }
    assigned_sentiment = assign_sentiment_to_sessions(sentiment, trading_dates, config)
    benchmark_returns = _benchmark_returns(price_groups, config.benchmark_ticker)

    rows: list[FeatureRow] = []
    for ticker in config.tickers:
        ticker_prices = price_groups.get(ticker, [])
        closes = [float(row.adjusted_close) for row in ticker_prices]
        volumes = [float(row.volume) for row in ticker_prices]
        macd, macd_signal = macd_series(closes)
        for index, current in enumerate(ticker_prices[:-1]):
            target = ticker_prices[index + 1]
            if current.trading_date < config.start_date or current.trading_date > config.end_date:
                continue
            if index < 25:
                continue
            cutoff = information_cutoff(current.trading_date, config)
            sentiment_features, latest_publication = _sentiment_features(
                ticker,
                index,
                ticker_prices,
                assigned_sentiment,
            )
            features: dict[str, float | int | None] = {
                "return_1d": pct_change(closes, index, 1),
                "return_3d": pct_change(closes, index, 3),
                "return_5d": pct_change(closes, index, 5),
                "return_20d": pct_change(closes, index, 20),
                "ma_5_deviation": moving_average_deviation(closes, index, 5),
                "ma_20_deviation": moving_average_deviation(closes, index, 20),
                "volume_change_1d": pct_change(volumes, index, 1),
                "volume_zscore_20d": rolling_zscore(volumes, index, 20),
                "volatility_5d": historical_volatility(closes, index, 5),
                "volatility_20d": historical_volatility(closes, index, 20),
                "rsi_14d": rsi(closes, index, 14),
                "macd_12_26": _round(macd[index]),
                "macd_signal_9": _round(macd_signal[index]),
                "benchmark_return_1d": benchmark_returns.get(current.trading_date),
                **sentiment_features,
            }
            forward_return = closes[index + 1] / closes[index] - 1.0
            rows.append(
                FeatureRow(
                    ticker=ticker,
                    feature_date=current.trading_date,
                    target_date=target.trading_date,
                    information_cutoff=cutoff,
                    latest_sentiment_published_at=latest_publication,
                    features=features,
                    forward_return_1d=_round(forward_return),
                    label_up=int(forward_return > 0),
                )
            )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.feature_date, row.ticker)))
    market_hash = _snapshot_hash([_price_payload(row) for row in prices])
    sentiment_hash = _snapshot_hash([_sentiment_payload(row) for row in sentiment])
    content = {
        "schema_version": "modeling-dataset-v1",
        "config": config.to_dict(),
        "market_snapshot_sha256": market_hash,
        "sentiment_snapshot_sha256": sentiment_hash,
        "rows": [row.to_dict() for row in ordered_rows],
    }
    return FeatureDataset(
        config=config,
        market_snapshot_sha256=market_hash,
        sentiment_snapshot_sha256=sentiment_hash,
        rows=ordered_rows,
        sha256=_canonical_hash(content),
    )


def _group_prices(
    prices: list[PriceObservation], config: FeatureConfig
) -> dict[str, list[PriceObservation]]:
    groups: dict[str, list[PriceObservation]] = defaultdict(list)
    seen: set[tuple[str, object]] = set()
    allowed = set(config.tickers)
    if config.benchmark_ticker:
        allowed.add(config.benchmark_ticker)
    for row in sorted(prices, key=lambda item: (item.ticker, item.trading_date)):
        if row.ticker not in allowed:
            continue
        key = (row.ticker, row.trading_date)
        if key in seen:
            raise ValueError(f"duplicate price observation: {row.ticker} {row.trading_date}")
        seen.add(key)
        groups[row.ticker].append(row)
    return dict(groups)


def _benchmark_returns(
    groups: dict[str, list[PriceObservation]], benchmark_ticker: str | None
) -> dict[object, float]:
    if not benchmark_ticker:
        return {}
    rows = groups.get(benchmark_ticker, [])
    closes = [float(row.adjusted_close) for row in rows]
    return {
        row.trading_date: value
        for index, row in enumerate(rows)
        if (value := pct_change(closes, index, 1)) is not None
    }


def _sentiment_features(
    ticker: str,
    index: int,
    prices: list[PriceObservation],
    assigned: dict[tuple[str, object], list[SentimentObservation]],
) -> tuple[dict[str, float | int | None], datetime | None]:
    same_day = assigned.get((ticker, prices[index].trading_date), [])
    audit_events = same_day
    output = _aggregate_sentiment(same_day, prefix="sentiment_1d")
    output.update(_aggregate_source_sentiment(same_day, prefix="sentiment_1d"))
    for window in (3, 5):
        start = max(0, index - window + 1)
        events = [
            event
            for price in prices[start : index + 1]
            for event in assigned.get((ticker, price.trading_date), [])
        ]
        output.update(_aggregate_sentiment(events, prefix=f"sentiment_{window}d"))
        output.update(_aggregate_source_sentiment(events, prefix=f"sentiment_{window}d"))
        if window == 5:
            audit_events = events
    publications = [
        event.published_at.replace(tzinfo=UTC)
        if event.published_at.tzinfo is None
        else event.published_at
        for event in audit_events
    ]
    return output, max(publications, default=None)


def _aggregate_source_sentiment(
    events: list[SentimentObservation], *, prefix: str
) -> dict[str, float | int | None]:
    output: dict[str, float | int | None] = {}
    groups = {
        "announcement": [event for event in events if event.source_type == "official_announcement"],
        "news": [event for event in events if event.source_type != "official_announcement"],
    }
    for source_name, source_events in groups.items():
        scores = [float(event.sentiment_score) for event in source_events]
        output[f"{prefix}_{source_name}_article_count"] = len(source_events)
        output[f"{prefix}_{source_name}_score_mean"] = (
            _round(sum(scores) / len(scores)) if scores else None
        )
    return output


def _aggregate_sentiment(
    events: list[SentimentObservation], *, prefix: str
) -> dict[str, float | int | None]:
    count = len(events)
    if not events:
        return {
            f"{prefix}_article_count": 0,
            f"{prefix}_positive_prob_mean": None,
            f"{prefix}_neutral_prob_mean": None,
            f"{prefix}_negative_prob_mean": None,
            f"{prefix}_score_mean": None,
            f"{prefix}_score_std": None,
            f"{prefix}_relevance_weighted_score": None,
            f"{prefix}_positive_ratio": None,
            f"{prefix}_negative_ratio": None,
        }
    scores = [float(event.sentiment_score) for event in events]
    weights = [float(event.relevance_score) for event in events]
    score_mean = sum(scores) / count
    score_variance = sum((score - score_mean) ** 2 for score in scores) / count
    weight_total = sum(weights)
    return {
        f"{prefix}_article_count": count,
        f"{prefix}_positive_prob_mean": _round(sum(float(e.positive_prob) for e in events) / count),
        f"{prefix}_neutral_prob_mean": _round(sum(float(e.neutral_prob) for e in events) / count),
        f"{prefix}_negative_prob_mean": _round(sum(float(e.negative_prob) for e in events) / count),
        f"{prefix}_score_mean": _round(score_mean),
        f"{prefix}_score_std": _round(math.sqrt(score_variance)),
        f"{prefix}_relevance_weighted_score": (
            _round(
                sum(score * weight for score, weight in zip(scores, weights, strict=True))
                / weight_total
            )
            if weight_total
            else None
        ),
        f"{prefix}_positive_ratio": _round(
            sum(e.predicted_label == "positive" for e in events) / count
        ),
        f"{prefix}_negative_ratio": _round(
            sum(e.predicted_label == "negative" for e in events) / count
        ),
    }


def _price_payload(row: PriceObservation) -> dict[str, object]:
    return {
        "ticker": row.ticker,
        "trading_date": row.trading_date.isoformat(),
        "open": format(row.open, "f"),
        "high": format(row.high, "f"),
        "low": format(row.low, "f"),
        "close": format(row.close, "f"),
        "adjusted_close": format(row.adjusted_close, "f"),
        "volume": row.volume,
    }


def _sentiment_payload(row: SentimentObservation) -> dict[str, object]:
    published = (
        row.published_at.replace(tzinfo=UTC)
        if row.published_at.tzinfo is None
        else row.published_at
    )
    return {
        "article_id": row.article_id,
        "ticker": row.ticker,
        "published_at": published.astimezone(UTC).isoformat(),
        "source_type": row.source_type,
        "relevance_score": format(row.relevance_score, "f"),
        "positive_prob": format(row.positive_prob, "f"),
        "neutral_prob": format(row.neutral_prob, "f"),
        "negative_prob": format(row.negative_prob, "f"),
        "sentiment_score": format(row.sentiment_score, "f"),
        "predicted_label": row.predicted_label,
    }


def _snapshot_hash(rows: list[dict[str, object]]) -> str:
    return _canonical_hash(sorted(rows, key=lambda row: json.dumps(row, sort_keys=True)))


def _canonical_hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _round(value: float) -> float:
    return round(value, 10)
