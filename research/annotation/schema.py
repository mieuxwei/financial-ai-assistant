from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SCHEMA_VERSION = "taiwan-financial-annotation-v1"
TAXONOMY_VERSION = "taiwan-event-taxonomy-v1"
LABEL_VERSION = "taiwan-impact-labels-v1"


class EventType(StrEnum):
    EARNINGS = "EARNINGS"
    REVENUE = "REVENUE"
    DIVIDEND = "DIVIDEND"
    BUYBACK = "BUYBACK"
    CAPITAL_INCREASE = "CAPITAL_INCREASE"
    CAPITAL_REDUCTION = "CAPITAL_REDUCTION"
    MERGERS_AND_ACQUISITIONS = "M&A"
    REGULATORY = "REGULATORY"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    GUIDANCE = "GUIDANCE"
    MATERIAL_TRANSACTION = "MATERIAL_TRANSACTION"
    OTHER = "OTHER"


class ImpactLabel(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    AMBIGUOUS = "AMBIGUOUS"


class ReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    CONFLICT = "CONFLICT"
    ADJUDICATED = "ADJUDICATED"
    EXCLUDED = "EXCLUDED"


class AnnotationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["taiwan-financial-annotation-v1"] = SCHEMA_VERSION
    taxonomy_version: Literal["taiwan-event-taxonomy-v1"] = TAXONOMY_VERSION
    label_version: Literal["taiwan-impact-labels-v1"] = LABEL_VERSION
    sample_id: str = Field(min_length=1, max_length=128)
    source_name: str = Field(min_length=1, max_length=80)
    source_type: str = Field(min_length=1, max_length=80)
    source_url: HttpUrl
    source_record_id: str | None = Field(default=None, max_length=256)
    published_at: datetime
    ticker: str = Field(pattern=r"^[0-9A-Z][0-9A-Z.\-]{0,19}$")
    entity_name: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=500)
    context: str | None = Field(default=None, max_length=1000)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_group_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    impact_label: ImpactLabel
    confidence: int = Field(ge=1, le=3)
    ambiguous_reason: str | None = Field(default=None, max_length=500)
    annotator_id: str = Field(min_length=1, max_length=64)
    review_status: ReviewStatus = ReviewStatus.DRAFT
    adjudicated_label: ImpactLabel | None = None
    include_for_training: bool = False
    exclusion_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_annotation_state(self) -> "AnnotationRecord":
        if self.impact_label is ImpactLabel.AMBIGUOUS and not self.ambiguous_reason:
            raise ValueError("AMBIGUOUS requires ambiguous_reason")
        if self.review_status is ReviewStatus.ADJUDICATED and self.adjudicated_label is None:
            raise ValueError("ADJUDICATED requires adjudicated_label")
        if self.review_status is ReviewStatus.EXCLUDED and not self.exclusion_reason:
            raise ValueError("EXCLUDED requires exclusion_reason")
        if self.include_for_training and self.review_status not in {
            ReviewStatus.REVIEWED,
            ReviewStatus.ADJUDICATED,
        }:
            raise ValueError("training records must be reviewed or adjudicated")
        return self
