from __future__ import annotations

import math
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pipelines.features.risk_builder import FEATURE_NAMES


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VolatilitySurprisePredictionRequest(StrictSchema):
    ticker: str = Field(min_length=1, max_length=20)
    as_of_date: date
    information_cutoff: datetime
    features: dict[str, float]

    @field_validator("information_cutoff")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("information_cutoff must be timezone-aware")
        return value

    @field_validator("features")
    @classmethod
    def require_frozen_features(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != set(FEATURE_NAMES):
            raise ValueError("features must exactly match risk-features-v1")
        if not all(math.isfinite(number) for number in value.values()):
            raise ValueError("features must contain only finite values")
        return value

    @model_validator(mode="after")
    def cutoff_matches_date(self) -> VolatilitySurprisePredictionRequest:
        if self.information_cutoff.date() != self.as_of_date:
            raise ValueError("information_cutoff date must match as_of_date")
        return self


class PredictionClaimBoundary(StrictSchema):
    research_signal_only: Literal[True]
    prospective_accuracy: Literal[False]
    price_direction_forecast: Literal[False]
    investment_advice: Literal[False]
    guaranteed_future_volatility: Literal[False]


class VolatilitySurprisePredictionResponse(StrictSchema):
    schema_version: Literal["volatility-surprise-prediction-response-v1"]
    ticker: str
    as_of_date: date
    information_cutoff: datetime
    predicted_volatility_surprise: str
    historical_percentile: float = Field(ge=0, le=100)
    risk_band: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    model_version: str
    feature_pipeline_version: str
    target_version: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claim_boundary: PredictionClaimBoundary


class IntelligenceTickerMatch(StrictSchema):
    ticker: str
    relevance_score: float = Field(ge=0, le=1)
    match_method: str


class IntelligenceSentiment(StrictSchema):
    status: Literal["SCORED", "ELIGIBLE_NOT_SCORED", "ABSTAIN"]
    output_type: str | None
    label: str | None
    positive_probability: float | None = Field(default=None, ge=0, le=1)
    neutral_probability: float | None = Field(default=None, ge=0, le=1)
    negative_probability: float | None = Field(default=None, ge=0, le=1)
    score: float | None = Field(default=None, ge=-1, le=1)
    model_version: str | None
    input_hash: str | None
    abstention_reason: str | None


class OfficialMetadata(StrictSchema):
    company_name: str | None
    clause: str | None
    fact_date: str | None


class EventIntelligence(StrictSchema):
    status: Literal["SIGNAL", "ABSTAIN"]
    normalized_event_type: str | None
    impact_proxy: str | None
    confidence: float = Field(ge=0, le=1)
    abstention_reason: str | None
    rule_revision: str
    sentiment_ground_truth: Literal[False]
    manual_review_used: Literal[False]


class IntelligenceLineage(StrictSchema):
    external_id: str | None
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sentiment_model_version: str | None


class IntelligenceClaimBoundary(StrictSchema):
    chinese_sentiment_validated: Literal[False]
    event_proxy_is_sentiment_ground_truth: Literal[False]
    llm_generated: Literal[False]
    track_a_dependency: Literal[False]


class FinancialIntelligenceItem(StrictSchema):
    schema_version: str
    item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: str
    source_type: str
    published_at: datetime
    language: str
    ticker_matches: list[IntelligenceTickerMatch]
    sentiment: IntelligenceSentiment
    official_metadata: OfficialMetadata
    event_intelligence: EventIntelligence
    deterministic_cue_terms: list[str]
    source_excerpt: str | None
    generated_summary: None
    lineage: IntelligenceLineage
    claim_boundary: IntelligenceClaimBoundary


class IntelligenceRetrievalBoundary(StrictSchema):
    database_only: Literal[True]
    external_api_called: Literal[False]
    model_inference_performed: Literal[False]
    llm_called: Literal[False]
    full_article_content_returned: Literal[False]


class FinancialIntelligenceResponse(StrictSchema):
    schema_version: Literal["financial-intelligence-response-v1"]
    ticker: str
    as_of_cutoff: datetime | None
    item_count: int = Field(ge=0)
    items: list[FinancialIntelligenceItem]
    intelligence_version: str
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_boundary: IntelligenceRetrievalBoundary
    disclaimer: str
