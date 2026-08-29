from __future__ import annotations

import hashlib
import json
import unicodedata
from bisect import bisect_left
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_CONFIG = Path("research/configs/b4_market_reaction_validation.v1.json")
PROTOCOL_VERSION = "b4-market-reaction-validation-v1"

TimestampBasis = Literal["OBSERVED_OFFSET", "SOURCE_CONTRACT_ASSUMPTION", "UNKNOWN"]


class TargetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    continuous: bool | None = None
    causal_claim: bool | None = None


class DeduplicationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exact_family_key: str
    source_priority: list[str] = Field(min_length=1)
    exact_duplicate_policy: str
    same_reaction_window_policy: str
    cross_split_family_policy: str


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str
    role: str
    b4_permission: str


class RepresentationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    encoder: str
    encoder_revision: str
    adapted_weight_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrain_encoder: Literal[False]
    availability_rule: str


class CandidateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str
    feature_group: str
    family: Literal["Ridge"]


class ChronologicalEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    random_split_allowed: Literal[False]
    preferred_design: Literal["expanding_window_rolling_origin"]
    inner_selection: str
    duplicate_family_isolation_required: Literal[True]
    minimum_outer_folds: int = Field(ge=2)
    minimum_events_per_evaluation_fold: int = Field(ge=20)


class DataSufficiencyGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_usable_event_windows: int = Field(ge=100)
    minimum_unique_tickers: int = Field(ge=2)
    minimum_calendar_years: int = Field(ge=2)
    minimum_outer_folds: int = Field(ge=2)
    minimum_events_per_evaluation_fold: int = Field(ge=20)
    minimum_reliable_timestamp_ratio: float = Field(ge=0, le=1)
    minimum_market_match_ratio: float = Field(ge=0, le=1)
    required_cross_source_dedup_coverage: float = Field(ge=0, le=1)


class ResearchSignalGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all_leakage_checks_required: Literal[True]
    minimum_median_outer_spearman: float
    minimum_text_minus_metadata_mean_spearman: float
    minimum_fraction_outer_folds_with_positive_text_increment: float = Field(ge=0, le=1)
    maximum_text_mae_relative_degradation: float = Field(ge=0)
    minimum_worst_outer_spearman: float


class SentimentBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED"]
    market_reaction_is_sentiment_ground_truth: Literal[False]
    retrain_sentiment_model: Literal[False]
    old_sentiment_gate_reused: Literal[False]


class B4Protocol(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    protocol_version: Literal["b4-market-reaction-validation-v1"]
    status: Literal["B4_PROTOCOL_FROZEN_BEFORE_MODEL_EVALUATION"]
    market_timezone: Literal["Asia/Taipei"]
    market_open: time
    market_close: time
    intraday_publication_policy: Literal[
        "ABSTAIN_DAILY_PRICE_CANNOT_ISOLATE_POST_PUBLICATION_REACTION"
    ]
    primary_target: TargetDefinition
    secondary_targets: list[TargetDefinition] = Field(min_length=1)
    timestamp_bases_allowed: list[str]
    deduplication: DeduplicationPolicy
    sources: list[SourcePolicy]
    representation: RepresentationPolicy
    candidate_models: list[CandidateModel]
    chronological_evaluation: ChronologicalEvaluation
    data_sufficiency_gate: DataSufficiencyGate
    research_signal_gate: ResearchSignalGate
    sentiment: SentimentBoundary
    prohibited_sources: list[str]
    on_insufficient_data: Literal["ABSTAIN_INSUFFICIENT_MARKET_REACTION_DATA"]
    next_unit_if_b4_complete: Literal["B5_NLP_INTELLIGENCE_INTEGRATION"]

    @model_validator(mode="after")
    def validate_boundaries(self) -> B4Protocol:
        if self.market_open >= self.market_close:
            raise ValueError("market open must precede close")
        if self.primary_target.causal_claim is not False:
            raise ValueError("B4 target cannot claim causal impact")
        if self.primary_target.continuous is not True:
            raise ValueError("B4 primary target must remain continuous")
        if len({item.source_id for item in self.sources}) != len(self.sources):
            raise ValueError("B4 source IDs must be unique")
        if [item.candidate_id for item in self.candidate_models] != [
            "market_only_ridge",
            "metadata_only_ridge",
            "bert_text_metadata_ridge",
        ]:
            raise ValueError("B4 compact model comparison is frozen")
        if "eland" not in self.prohibited_sources:
            raise ValueError("eLAND must remain prohibited")
        if self.representation.retrain_encoder:
            raise ValueError("B4 cannot retrain the B3 encoder")
        return self


@dataclass(frozen=True)
class ReactionWindow:
    status: str
    anchor_session: date | None
    reaction_session: date | None
    local_publication: datetime | None


@dataclass(frozen=True)
class SufficiencyObservation:
    usable_event_windows: int
    unique_tickers: int
    calendar_years: int
    outer_folds: int
    minimum_events_in_any_evaluation_fold: int
    reliable_timestamp_ratio: float
    market_match_ratio: float
    cross_source_dedup_coverage: float


def load_protocol(path: Path = DEFAULT_CONFIG) -> B4Protocol:
    return B4Protocol.model_validate_json(path.read_text(encoding="utf-8"))


def align_reaction_window(
    published_at: datetime,
    sessions: list[date],
    protocol: B4Protocol,
    *,
    timestamp_basis: TimestampBasis,
) -> ReactionWindow:
    if published_at.tzinfo is None or timestamp_basis not in protocol.timestamp_bases_allowed:
        return ReactionWindow("ABSTAIN_TIMESTAMP", None, None, None)
    ordered = sorted(set(sessions))
    if not ordered:
        return ReactionWindow("ABSTAIN_NO_EXCHANGE_CALENDAR", None, None, None)

    local = published_at.astimezone(ZoneInfo(protocol.market_timezone))
    day_index = bisect_left(ordered, local.date())
    is_session = day_index < len(ordered) and ordered[day_index] == local.date()

    if is_session and protocol.market_open <= local.time() <= protocol.market_close:
        return ReactionWindow("ABSTAIN_INTRADAY_PRICE_UNAVAILABLE", None, None, local)

    if is_session and local.time() > protocol.market_close:
        anchor_index = day_index
        reaction_index = day_index + 1
    else:
        reaction_index = day_index
        anchor_index = reaction_index - 1

    if anchor_index < 0:
        return ReactionWindow("ABSTAIN_MISSING_ANCHOR_SESSION", None, None, local)
    if reaction_index >= len(ordered):
        return ReactionWindow("ABSTAIN_INCOMPLETE_REACTION_WINDOW", None, None, local)
    return ReactionWindow("ELIGIBLE", ordered[anchor_index], ordered[reaction_index], local)


def normalize_subject(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return " ".join(normalized.split())


def event_family_id(ticker: str, subject: str, publication_local_date: date) -> str:
    normalized = normalize_subject(subject)
    payload = f"{ticker}\x1f{normalized}\x1f{publication_local_date.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()


def ticker_window_id(ticker: str, window: ReactionWindow) -> str:
    if window.status != "ELIGIBLE" or window.anchor_session is None:
        raise ValueError("only eligible windows have a ticker-window identity")
    assert window.reaction_session is not None
    payload = (
        f"{ticker}\x1f{window.anchor_session.isoformat()}"
        f"\x1f{window.reaction_session.isoformat()}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def assess_data_sufficiency(
    observation: SufficiencyObservation,
    gate: DataSufficiencyGate,
) -> dict[str, object]:
    checks = {
        "usable_event_windows": (
            observation.usable_event_windows >= gate.minimum_usable_event_windows
        ),
        "unique_tickers": observation.unique_tickers >= gate.minimum_unique_tickers,
        "calendar_years": observation.calendar_years >= gate.minimum_calendar_years,
        "outer_folds": observation.outer_folds >= gate.minimum_outer_folds,
        "events_per_evaluation_fold": (
            observation.minimum_events_in_any_evaluation_fold
            >= gate.minimum_events_per_evaluation_fold
        ),
        "reliable_timestamp_ratio": (
            observation.reliable_timestamp_ratio >= gate.minimum_reliable_timestamp_ratio
        ),
        "market_match_ratio": observation.market_match_ratio >= gate.minimum_market_match_ratio,
        "cross_source_dedup_coverage": (
            observation.cross_source_dedup_coverage
            >= gate.required_cross_source_dedup_coverage
        ),
    }
    passed = all(checks.values())
    return {
        "observation": asdict(observation),
        "checks": checks,
        "failed_checks": [name for name, result in checks.items() if not result],
        "passed": passed,
        "maturity": (
            "READY_FOR_CHRONOLOGICAL_MODEL_EVALUATION"
            if passed
            else "ABSTAIN_INSUFFICIENT_MARKET_REACTION_DATA"
        ),
    }


def sha256_json(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
