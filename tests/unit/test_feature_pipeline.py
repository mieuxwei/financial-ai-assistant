import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from pipelines.features import (
    FeatureConfig,
    PriceObservation,
    SentimentObservation,
    build_modeling_dataset,
)
from pipelines.features.snapshot import write_feature_dataset


def trading_dates(count: int) -> list[date]:
    output = []
    current = date(2026, 1, 5)
    while len(output) < count:
        if current.weekday() < 5:
            output.append(current)
        current += timedelta(days=1)
    return output


def prices(*, target_override: Decimal | None = None) -> list[PriceObservation]:
    rows = []
    for index, trading_date in enumerate(trading_dates(32)):
        close = Decimal(100 + index)
        if index == 26 and target_override is not None:
            close = target_override
        rows.append(
            PriceObservation(
                ticker="2330",
                trading_date=trading_date,
                open=close - 1,
                high=close + 1,
                low=close - 2,
                close=close,
                adjusted_close=close,
                volume=1000 + index * 20,
            )
        )
    return rows


def event(identity: str, published_at: datetime) -> SentimentObservation:
    return SentimentObservation(
        article_id=identity,
        ticker="2330",
        published_at=published_at,
        source_type="official_announcement",
        relevance_score=Decimal("1"),
        positive_prob=Decimal("0.8"),
        neutral_prob=Decimal("0.15"),
        negative_prob=Decimal("0.05"),
        sentiment_score=Decimal("0.75"),
        predicted_label="positive",
    )


def config() -> FeatureConfig:
    dates = trading_dates(32)
    return FeatureConfig(
        tickers=("2330",),
        start_date=dates[0],
        end_date=dates[-1],
        market_source="fixture",
        sentiment_model_version="fixture-model@revision",
    )


def test_cutoff_assigns_after_close_and_weekend_news_to_next_session() -> None:
    dates = trading_dates(32)
    timezone = ZoneInfo("Asia/Taipei")
    before_close = datetime.combine(dates[25], time(13, 29), tzinfo=timezone)
    after_close = datetime.combine(dates[25], time(13, 31), tzinfo=timezone)
    weekend = datetime.combine(dates[25] + timedelta(days=1), time(9), tzinfo=timezone)

    dataset = build_modeling_dataset(
        prices(),
        [event("before", before_close), event("after", after_close), event("weekend", weekend)],
        config(),
    )
    first, second = dataset.rows[:2]

    assert first.feature_date == dates[25]
    assert first.features["sentiment_1d_article_count"] == 1
    assert first.features["sentiment_1d_announcement_article_count"] == 1
    assert first.features["sentiment_1d_news_article_count"] == 0
    assert second.feature_date == dates[26]
    assert second.features["sentiment_1d_article_count"] == 2
    assert first.latest_sentiment_published_at is not None
    assert first.latest_sentiment_published_at <= first.information_cutoff
    assert second.latest_sentiment_published_at is not None
    assert second.latest_sentiment_published_at <= second.information_cutoff


def test_future_price_changes_label_but_not_same_day_features() -> None:
    baseline = build_modeling_dataset(prices(), [], config())
    revised = build_modeling_dataset(prices(target_override=Decimal("90")), [], config())
    baseline_row = baseline.rows[0]
    revised_row = revised.rows[0]

    assert baseline_row.feature_date == revised_row.feature_date
    assert baseline_row.features == revised_row.features
    assert baseline_row.label_up == 1
    assert revised_row.label_up == 0
    assert baseline_row.target_date > baseline_row.feature_date
    assert baseline_row.features["rsi_14d"] == 100.0


def test_dataset_hash_is_reproducible_and_missing_sentiment_stays_missing() -> None:
    first = build_modeling_dataset(prices(), [], config())
    second = build_modeling_dataset(list(reversed(prices())), [], config())

    assert first.sha256 == second.sha256
    assert first.market_snapshot_sha256 == second.market_snapshot_sha256
    assert first.sentiment_snapshot_sha256 == second.sentiment_snapshot_sha256
    assert first.rows[0].features["sentiment_1d_article_count"] == 0
    assert first.rows[0].features["sentiment_1d_score_mean"] is None
    assert first.rows[0].features["sentiment_5d_announcement_score_mean"] is None
    assert first.rows[0].latest_sentiment_published_at is None
    assert first.rows[0].information_cutoff.tzinfo == UTC


def test_versioned_snapshot_contains_rebuild_contract(tmp_path: Path) -> None:
    dataset = build_modeling_dataset(prices(), [], config())
    output = tmp_path / "modeling-dataset.json"

    write_feature_dataset(output, dataset)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "modeling-dataset-v1"
    assert payload["config"] == config().to_dict()
    assert payload["row_count"] == len(dataset.rows)
    assert payload["sha256"] == dataset.sha256
