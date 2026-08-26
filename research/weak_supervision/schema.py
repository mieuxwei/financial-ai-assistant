from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research.annotation.schema import EventType, ImpactLabel

WEAK_VOTE_SCHEMA_VERSION = "taiwan-weak-vote-v1"
AGGREGATION_PROTOCOL_VERSION = "taiwan-weak-aggregation-v1"


class WeakVote(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["taiwan-weak-vote-v1"] = WEAK_VOTE_SCHEMA_VERSION
    labeling_function_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    labeling_function_revision: str = Field(min_length=1, max_length=128)
    source_type: Literal[
        "official_category",
        "deterministic_rule",
        "local_model",
        "translation_finbert",
        "llm_structured",
    ]
    impact_label: ImpactLabel | None = None
    normalized_event_type: EventType | None = None
    confidence: float = Field(ge=0, le=1)
    abstention_reason: str | None = Field(default=None, max_length=200)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_version: str | None = Field(default=None, max_length=300)
    prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_vote_contract(self) -> WeakVote:
        has_signal = self.impact_label is not None or self.normalized_event_type is not None
        if not has_signal and not self.abstention_reason:
            raise ValueError("an empty vote requires abstention_reason")
        if not has_signal and self.confidence != 0:
            raise ValueError("an abstained vote must have zero confidence")
        if has_signal and self.confidence == 0:
            raise ValueError("a signal vote must have positive confidence")
        if has_signal and self.abstention_reason:
            raise ValueError("a signal vote cannot also abstain")
        if self.source_type in {"local_model", "translation_finbert", "llm_structured"}:
            if not self.model_version:
                raise ValueError("model-backed votes require model_version")
        if self.source_type == "llm_structured" and not self.prompt_sha256:
            raise ValueError("LLM votes require prompt_sha256")
        return self


class WeakAggregationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    protocol_version: Literal["taiwan-weak-aggregation-v1"] = (
        AGGREGATION_PROTOCOL_VERSION
    )
    minimum_sources: int = Field(ge=2, le=10)
    minimum_margin: float = Field(ge=0, le=1)
    labeling_function_weights: dict[str, float] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_weights(self) -> WeakAggregationConfig:
        if any(weight <= 0 or weight > 10 for weight in self.labeling_function_weights.values()):
            raise ValueError("labeling-function weights must be in (0, 10]")
        return self
