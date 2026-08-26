from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL_VERSION = "market-reaction-v1"
RETURN_QUANTUM = Decimal("0.0000000001")


class ReactionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    protocol_version: Literal["market-reaction-v1"] = PROTOCOL_VERSION
    market_timezone: str = "Asia/Taipei"
    information_cutoff: time
    horizons: dict[str, int] = Field(min_length=1)
    neutral_thresholds: dict[str, Decimal] = Field(min_length=1)
    threshold_version: str = Field(min_length=1, max_length=100)
    benchmark_id: str = Field(min_length=1, max_length=100)
    benchmark_source: str = Field(min_length=1, max_length=200)
    stock_source: str = Field(min_length=1, max_length=100)
    train_end: date
    validation_end: date
    max_abs_raw_return: Decimal = Field(gt=0, le=1)

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not name or sessions < 1 for name, sessions in value.items()):
            raise ValueError("horizon names must be non-empty and sessions must be positive")
        return value

    @field_validator("neutral_thresholds")
    @classmethod
    def validate_thresholds(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        if any(threshold < 0 or threshold >= 1 for threshold in value.values()):
            raise ValueError("neutral thresholds must be in [0, 1)")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> ReactionConfig:
        if set(self.horizons) != set(self.neutral_thresholds):
            raise ValueError("horizons and neutral_thresholds must have identical keys")
        if self.train_end >= self.validation_end:
            raise ValueError("train_end must precede validation_end")
        ZoneInfo(self.market_timezone)
        return self


@dataclass(frozen=True)
class ReactionEvent:
    article_id: str
    event_group_id: str
    ticker: str
    published_at: datetime


@dataclass(frozen=True)
class ReactionPrice:
    ticker: str
    trading_date: date
    adjusted_close: Decimal

    def __post_init__(self) -> None:
        if self.adjusted_close <= 0:
            raise ValueError("adjusted_close must be positive")


def build_market_reaction_labels(
    events: list[ReactionEvent],
    stock_prices: list[ReactionPrice],
    benchmark_prices: dict[date, Decimal],
    config: ReactionConfig,
    *,
    market_snapshot_sha256: str,
) -> list[dict[str, object]]:
    if len(market_snapshot_sha256) != 64:
        raise ValueError("market_snapshot_sha256 must be a SHA-256 digest")
    sessions = sorted(benchmark_prices)
    if len(sessions) != len(set(sessions)) or any(benchmark_prices[item] <= 0 for item in sessions):
        raise ValueError("benchmark sessions must be unique and positive")
    stock_by_key = {
        (price.ticker, price.trading_date): price.adjusted_close for price in stock_prices
    }
    if len(stock_by_key) != len(stock_prices):
        raise ValueError("stock prices must be unique by ticker and trading date")

    rows = []
    timezone = ZoneInfo(config.market_timezone)
    for event in sorted(
        events,
        key=lambda item: (
            item.published_at,
            item.event_group_id,
            item.ticker,
            item.article_id,
        ),
    ):
        if event.published_at.tzinfo is None:
            rows.extend(
                _abstained_rows(
                    event,
                    config,
                    market_snapshot_sha256,
                    "ABSTAIN_TIMESTAMP",
                )
            )
            continue
        local = event.published_at.astimezone(timezone)
        effective_index = _effective_session_index(
            sessions, local, config.information_cutoff
        )
        split = _split_assignment(local.date(), config)
        if effective_index is None:
            rows.extend(
                _abstained_rows(
                    event,
                    config,
                    market_snapshot_sha256,
                    "ABSTAIN_NO_EFFECTIVE_SESSION",
                    split=split,
                )
            )
            continue
        if effective_index == 0:
            rows.extend(
                _abstained_rows(
                    event,
                    config,
                    market_snapshot_sha256,
                    "ABSTAIN_MISSING_ANCHOR_SESSION",
                    effective_session=sessions[effective_index],
                    split=split,
                )
            )
            continue

        effective_session = sessions[effective_index]
        anchor_session = sessions[effective_index - 1]
        information_set = _sha256(
            f"{event.ticker}\x1f{effective_session.isoformat()}"
        )
        for horizon, session_count in config.horizons.items():
            end_index = effective_index + session_count - 1
            if end_index >= len(sessions):
                rows.append(
                    _base_row(
                        event,
                        horizon,
                        config,
                        market_snapshot_sha256,
                        split,
                        effective_session=effective_session,
                        anchor_session=anchor_session,
                        information_set=information_set,
                        abstention_reason="ABSTAIN_INCOMPLETE_HORIZON",
                    )
                )
                continue
            end_session = sessions[end_index]
            stock_anchor = stock_by_key.get((event.ticker, anchor_session))
            stock_end = stock_by_key.get((event.ticker, end_session))
            if stock_anchor is None or stock_end is None:
                rows.append(
                    _base_row(
                        event,
                        horizon,
                        config,
                        market_snapshot_sha256,
                        split,
                        effective_session=effective_session,
                        anchor_session=anchor_session,
                        end_session=end_session,
                        information_set=information_set,
                        abstention_reason="ABSTAIN_MISSING_STOCK_PRICE",
                    )
                )
                continue
            benchmark_anchor = benchmark_prices.get(anchor_session)
            benchmark_end = benchmark_prices.get(end_session)
            if benchmark_anchor is None or benchmark_end is None:
                rows.append(
                    _base_row(
                        event,
                        horizon,
                        config,
                        market_snapshot_sha256,
                        split,
                        effective_session=effective_session,
                        anchor_session=anchor_session,
                        end_session=end_session,
                        information_set=information_set,
                        abstention_reason="ABSTAIN_MISSING_BENCHMARK_PRICE",
                    )
                )
                continue
            raw_return = stock_end / stock_anchor - 1
            if abs(raw_return) > config.max_abs_raw_return:
                rows.append(
                    _base_row(
                        event,
                        horizon,
                        config,
                        market_snapshot_sha256,
                        split,
                        effective_session=effective_session,
                        anchor_session=anchor_session,
                        end_session=end_session,
                        information_set=information_set,
                        abstention_reason="ABSTAIN_PRICE_ANOMALY",
                    )
                )
                continue
            benchmark_return = benchmark_end / benchmark_anchor - 1
            abnormal_return = raw_return - benchmark_return
            threshold = config.neutral_thresholds[horizon]
            rows.append(
                {
                    **_base_row(
                        event,
                        horizon,
                        config,
                        market_snapshot_sha256,
                        split,
                        effective_session=effective_session,
                        anchor_session=anchor_session,
                        end_session=end_session,
                        information_set=information_set,
                    ),
                    "raw_return": _format_return(raw_return),
                    "benchmark_return": _format_return(benchmark_return),
                    "abnormal_return": _format_return(abnormal_return),
                    "reaction_class": _reaction_class(abnormal_return, threshold),
                    "abstained": False,
                    "abstention_reason": None,
                }
            )
    return rows


def reaction_snapshot_sha256(rows: list[dict[str, object]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _effective_session_index(
    sessions: list[date], published_at: datetime, cutoff: time
) -> int | None:
    candidate = published_at.date()
    index = bisect_left(sessions, candidate)
    if index >= len(sessions):
        return None
    if sessions[index] == candidate and published_at.timetz().replace(tzinfo=None) > cutoff:
        index += 1
    return index if index < len(sessions) else None


def _split_assignment(value: date, config: ReactionConfig) -> str:
    if value <= config.train_end:
        return "train"
    if value <= config.validation_end:
        return "validation"
    return "test"


def _reaction_class(value: Decimal, threshold: Decimal) -> str:
    if value > threshold:
        return "POSITIVE_REACTION"
    if value < -threshold:
        return "NEGATIVE_REACTION"
    return "NEUTRAL_REACTION"


def _format_return(value: Decimal) -> str:
    return format(value.quantize(RETURN_QUANTUM), "f")


def _abstained_rows(
    event: ReactionEvent,
    config: ReactionConfig,
    market_snapshot_sha256: str,
    reason: str,
    *,
    effective_session: date | None = None,
    split: str = "unassigned",
) -> list[dict[str, object]]:
    return [
        _base_row(
            event,
            horizon,
            config,
            market_snapshot_sha256,
            split,
            effective_session=effective_session,
            abstention_reason=reason,
        )
        for horizon in config.horizons
    ]


def _base_row(
    event: ReactionEvent,
    horizon: str,
    config: ReactionConfig,
    market_snapshot_sha256: str,
    split: str,
    *,
    effective_session: date | None = None,
    anchor_session: date | None = None,
    end_session: date | None = None,
    information_set: str | None = None,
    abstention_reason: str | None = None,
) -> dict[str, object]:
    return {
        "article_id": event.article_id,
        "event_group_id": event.event_group_id,
        "ticker": event.ticker,
        "published_at": event.published_at.isoformat(),
        "timezone": config.market_timezone,
        "information_cutoff": config.information_cutoff.isoformat(),
        "effective_session": effective_session.isoformat() if effective_session else None,
        "anchor_session": anchor_session.isoformat() if anchor_session else None,
        "end_session": end_session.isoformat() if end_session else None,
        "horizon": horizon,
        "horizon_sessions": config.horizons[horizon],
        "raw_return": None,
        "benchmark_return": None,
        "abnormal_return": None,
        "reaction_class": None,
        "neutral_threshold": _format_return(config.neutral_thresholds[horizon]),
        "threshold_version": config.threshold_version,
        "benchmark_id": config.benchmark_id,
        "benchmark_source": config.benchmark_source,
        "stock_source": config.stock_source,
        "market_snapshot_sha256": market_snapshot_sha256,
        "ticker_session_information_set": information_set,
        "split_assignment": split,
        "protocol_version": config.protocol_version,
        "abstained": abstention_reason is not None,
        "abstention_reason": abstention_reason,
        "manual_labels_used": False,
        "sentiment_ground_truth": False,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
