from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_CONFIG = Path("research/configs/b5_nlp_intelligence_integration.v1.json")


class B5IntelligenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["b5-financial-intelligence-v1"]
    f8_config_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    b4_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    market_reaction: dict[str, Any]
    chinese_linguistic_sentiment: dict[str, Any]
    event_class: dict[str, Any]
    media_tone: dict[str, Any]
    representation: dict[str, Any]
    source_boundary: dict[str, Any]
    band_copy_zh_tw: dict[str, str]
    model_training_performed_in_b5: Literal[False]
    provider_calls_performed_in_b5: Literal[False]
    track_a_modified: Literal[False]
    gas_line_modified: Literal[False]
    deployed: Literal[False]

    @model_validator(mode="after")
    def validate_boundaries(self) -> B5IntelligenceConfig:
        reaction = self.market_reaction
        if reaction.get("maturity") != "AUTOMATED_SIGNAL_ONLY":
            raise ValueError("B4 maturity must remain AUTOMATED_SIGNAL_ONLY")
        if reaction.get("direction_status") != "ABSTAIN_DIRECTION_NOT_SUPPORTED":
            raise ValueError("B5 direction must abstain")
        sentiment = self.chinese_linguistic_sentiment
        if sentiment.get("reason") != "CHINESE_SENTIMENT_NOT_VALIDATED":
            raise ValueError("Chinese sentiment abstention drifted")
        if not sentiment.get("probabilities_must_be_null"):
            raise ValueError("Chinese sentiment probabilities must remain null")
        if self.source_boundary.get("provider_call_on_request") is not False:
            raise ValueError("request-time provider calls are prohibited")
        if self.representation.get("return_direction_prediction_supported") is not False:
            raise ValueError("BERT cannot be advertised for direction prediction")
        return self

    @property
    def canonical_sha256(self) -> str:
        body = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


def load_b5_intelligence_config(path: Path = DEFAULT_CONFIG) -> B5IntelligenceConfig:
    return B5IntelligenceConfig.model_validate_json(path.read_text(encoding="utf-8"))


def assemble_b5_intelligence(
    config: B5IntelligenceConfig,
    *,
    source: str,
    source_type: str,
    published_at: datetime,
    language: str,
    metadata: dict[str, object],
    requested_cutoff: datetime | None,
) -> dict[str, object]:
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise ValueError("B5 publication timestamp must be timezone-aware")
    if requested_cutoff is not None and (
        requested_cutoff.tzinfo is None or requested_cutoff.utcoffset() is None
    ):
        raise ValueError("B5 cutoff must be timezone-aware")

    is_chinese = language.casefold().startswith("zh")
    sentiment = {
        "status": "ABSTAIN" if is_chinese else "NOT_APPLICABLE_USE_F8_LANGUAGE_ROUTE",
        "maturity": "ABSTAIN" if is_chinese else "NOT_APPLICABLE",
        "polarity": None,
        "positive_probability": None,
        "neutral_probability": None,
        "negative_probability": None,
        "reason": "CHINESE_SENTIMENT_NOT_VALIDATED" if is_chinese else None,
    }
    event_class = _event_class(source, metadata)
    reaction = _reaction(config, metadata, published_at, requested_cutoff)
    return {
        "contract_version": config.contract_version,
        "event_classification": event_class,
        "linguistic_sentiment": sentiment,
        "market_reaction": reaction,
        "media_tone": {
            "status": "UNAVAILABLE_OR_CONDITIONAL",
            "output_type": "MEDIA_TONE_PROXY",
            "tone": None,
        },
        "representation": {
            **config.representation,
            "used_for_market_reaction_prediction": False,
        },
        "lineage": {
            "b5_config_sha256": config.canonical_sha256,
            "b4_result_sha256": config.b4_result_sha256,
            "source": source,
            "source_type": source_type,
            "publication_cutoff": published_at.isoformat(),
            "availability_timestamp": reaction["availability_timestamp"],
        },
        "limitations": [
            config.band_copy_zh_tw["direction"],
            config.band_copy_zh_tw["sentiment"],
            config.band_copy_zh_tw["disclaimer"],
        ],
    }


def _event_class(source: str, metadata: dict[str, object]) -> dict[str, object]:
    values = (
        metadata.get("event_class"),
        metadata.get("event_confidence"),
        metadata.get("rule_version"),
    )
    if not source.casefold().startswith("twmd") or any(value is None for value in values):
        return {
            "status": "UNAVAILABLE",
            "event_class": None,
            "confidence": None,
            "rule_version": None,
            "source": None,
            "sentiment_ground_truth": False,
            "market_direction": False,
        }
    confidence = float(metadata["event_confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("TWMD event confidence must be between zero and one")
    return {
        "status": "INFERRED_STRUCTURED_TAXONOMY",
        "event_class": str(metadata["event_class"]),
        "confidence": confidence,
        "rule_version": str(metadata["rule_version"]),
        "source": "TWMD",
        "sentiment_ground_truth": False,
        "market_direction": False,
    }


def _reaction(
    config: B5IntelligenceConfig,
    metadata: dict[str, object],
    published_at: datetime,
    requested_cutoff: datetime | None,
) -> dict[str, object]:
    unavailable = {
        "status": "UNAVAILABLE_NO_STORED_B4_SIGNAL",
        "maturity": "AUTOMATED_SIGNAL_ONLY",
        "reaction_magnitude_score": None,
        "historical_percentile": None,
        "communication_band": None,
        "direction": None,
        "direction_status": "ABSTAIN_DIRECTION_NOT_SUPPORTED",
        "model_version": config.market_reaction["model_version"],
        "reference_version": config.market_reaction["reference_version"],
        "availability_timestamp": None,
        "disclaimer": config.band_copy_zh_tw["disclaimer"],
    }
    required = ("b5_reaction_magnitude_score", "b5_historical_percentile", "b5_signal_available_at")
    if any(metadata.get(name) is None for name in required):
        return unavailable
    available_at = datetime.fromisoformat(str(metadata["b5_signal_available_at"]))
    if available_at.tzinfo is None or available_at.utcoffset() is None:
        return {**unavailable, "status": "ABSTAIN_UNCERTAIN_AVAILABILITY_TIMESTAMP"}
    if available_at < published_at or (requested_cutoff and available_at > requested_cutoff):
        return {**unavailable, "status": "ABSTAIN_SIGNAL_NOT_AVAILABLE_AT_CUTOFF"}
    score = float(metadata["b5_reaction_magnitude_score"])
    percentile = float(metadata["b5_historical_percentile"])
    if not math.isfinite(score) or score < 0 or not 0 <= percentile <= 100:
        raise ValueError("stored B5 reaction signal is invalid")
    cutoffs = config.market_reaction["score_cutoffs"]
    bands = config.market_reaction["bands"]
    band_index = sum(score >= float(cutoff) for cutoff in cutoffs)
    return {
        **unavailable,
        "status": "AVAILABLE_STORED_RESEARCH_SIGNAL",
        "reaction_magnitude_score": score,
        "historical_percentile": percentile,
        "communication_band": bands[band_index],
        "availability_timestamp": available_at.isoformat(),
    }
