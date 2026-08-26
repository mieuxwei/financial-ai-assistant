from datetime import UTC, date, datetime, time
from decimal import Decimal

from research.evaluation.market_reaction import (
    ReactionConfig,
    ReactionEvent,
    ReactionPrice,
    build_market_reaction_labels,
    reaction_snapshot_sha256,
)


def _config() -> ReactionConfig:
    return ReactionConfig.model_validate(
        {
            "information_cutoff": time(13, 30),
            "horizons": {"next_session": 1, "1d": 1, "3d": 3},
            "neutral_thresholds": {
                "next_session": "0.01",
                "1d": "0.01",
                "3d": "0.02",
            },
            "threshold_version": "test-v1",
            "benchmark_id": "TAIEX_TOTAL_RETURN",
            "benchmark_source": "synthetic",
            "stock_source": "synthetic",
            "train_end": "2024-12-31",
            "validation_end": "2025-12-31",
            "max_abs_raw_return": "0.5",
        }
    )


def _prices() -> tuple[list[ReactionPrice], dict[date, Decimal]]:
    values = {
        date(2024, 1, 2): "100",
        date(2024, 1, 3): "103",
        date(2024, 1, 6): "101",
        date(2024, 1, 7): "106",
    }
    prices = [
        ReactionPrice(ticker="2330", trading_date=day, adjusted_close=Decimal(value))
        for day, value in values.items()
    ]
    benchmark = {
        date(2024, 1, 2): Decimal("1000"),
        date(2024, 1, 3): Decimal("1010"),
        date(2024, 1, 6): Decimal("1020"),
        date(2024, 1, 7): Decimal("1030"),
    }
    return prices, benchmark


def _event(published_at: datetime, article_id: str = "article-1") -> ReactionEvent:
    return ReactionEvent(
        article_id=article_id,
        event_group_id="group-1",
        ticker="2330",
        published_at=published_at,
    )


def test_before_cutoff_maps_to_same_session_and_calculates_returns() -> None:
    prices, benchmark = _prices()
    rows = build_market_reaction_labels(
        [_event(datetime(2024, 1, 3, 5, tzinfo=UTC))],
        prices,
        benchmark,
        _config(),
        market_snapshot_sha256="a" * 64,
    )

    one_day = next(row for row in rows if row["horizon"] == "1d")
    three_day = next(row for row in rows if row["horizon"] == "3d")
    assert one_day["effective_session"] == "2024-01-03"
    assert one_day["anchor_session"] == "2024-01-02"
    assert one_day["raw_return"] == "0.0300000000"
    assert one_day["benchmark_return"] == "0.0100000000"
    assert one_day["abnormal_return"] == "0.0200000000"
    assert one_day["reaction_class"] == "POSITIVE_REACTION"
    assert three_day["end_session"] == "2024-01-07"
    assert three_day["reaction_class"] == "POSITIVE_REACTION"
    assert all(row["manual_labels_used"] is False for row in rows)
    assert len(reaction_snapshot_sha256(rows)) == 64


def test_after_cutoff_and_weekend_map_to_next_observed_session() -> None:
    prices, benchmark = _prices()
    events = [
        _event(datetime(2024, 1, 3, 6, tzinfo=UTC), "after-cutoff"),
        _event(datetime(2024, 1, 4, 20, tzinfo=UTC), "weekend"),
    ]
    rows = build_market_reaction_labels(
        events,
        prices,
        benchmark,
        _config(),
        market_snapshot_sha256="b" * 64,
    )

    one_day = [row for row in rows if row["horizon"] == "1d"]
    assert {row["effective_session"] for row in one_day} == {"2024-01-06"}
    assert {row["anchor_session"] for row in one_day} == {"2024-01-03"}
    three_day = [row for row in rows if row["horizon"] == "3d"]
    assert all(row["abstention_reason"] == "ABSTAIN_INCOMPLETE_HORIZON" for row in three_day)


def test_naive_timestamp_and_missing_stock_prices_abstain() -> None:
    _, benchmark = _prices()
    naive_rows = build_market_reaction_labels(
        [_event(datetime(2024, 1, 3, 12))],
        [],
        benchmark,
        _config(),
        market_snapshot_sha256="c" * 64,
    )
    assert all(row["abstention_reason"] == "ABSTAIN_TIMESTAMP" for row in naive_rows)

    missing_rows = build_market_reaction_labels(
        [_event(datetime(2024, 1, 3, 5, tzinfo=UTC))],
        [],
        benchmark,
        _config(),
        market_snapshot_sha256="d" * 64,
    )
    assert all(row["abstention_reason"] == "ABSTAIN_MISSING_STOCK_PRICE" for row in missing_rows)


def test_future_price_mutation_changes_only_target_side_values() -> None:
    prices, benchmark = _prices()
    event = _event(datetime(2024, 1, 3, 5, tzinfo=UTC))
    baseline = build_market_reaction_labels(
        [event], prices, benchmark, _config(), market_snapshot_sha256="e" * 64
    )
    mutated_prices = [
        ReactionPrice(
            ticker=row.ticker,
            trading_date=row.trading_date,
            adjusted_close=(
                Decimal("110") if row.trading_date == date(2024, 1, 7) else row.adjusted_close
            ),
        )
        for row in prices
    ]
    mutated = build_market_reaction_labels(
        [event], mutated_prices, benchmark, _config(), market_snapshot_sha256="f" * 64
    )
    baseline_three_day = next(row for row in baseline if row["horizon"] == "3d")
    mutated_three_day = next(row for row in mutated if row["horizon"] == "3d")

    assert baseline_three_day["abnormal_return"] != mutated_three_day["abnormal_return"]
    for field in (
        "article_id",
        "event_group_id",
        "ticker",
        "published_at",
        "effective_session",
        "anchor_session",
        "horizon",
        "split_assignment",
    ):
        assert baseline_three_day[field] == mutated_three_day[field]
