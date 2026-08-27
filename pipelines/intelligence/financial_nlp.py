from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from pipelines.news.types import NewsItem, TickerMatch
from pipelines.sentiment.finbert import DEFAULT_MODEL_ID, DEFAULT_MODEL_REVISION
from pipelines.sentiment.text import build_sentiment_text, sentiment_input_hash
from pipelines.sentiment.types import SentimentPrediction
from research.weak_supervision.deterministic import (
    EVENT_TERMS,
    NEGATIVE_TERMS,
    POSITIVE_TERMS,
    RULE_REVISION,
    deterministic_rule_vote,
)


class FinancialNlpIntelligenceConfig(BaseModel):
    """Frozen F8 configuration with validation of the non-negotiable boundaries."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    intelligence_version: str
    analysis_version: str
    report_version: str
    english_sentiment: dict[str, Any]
    taiwan_sentiment: dict[str, Any]
    taiwan_event_intelligence: dict[str, Any]
    product_capabilities: dict[str, str]
    active_source_roles: dict[str, str]
    eland: dict[str, Any]
    historical_evidence_files: dict[str, str]
    output_contract: dict[str, Any]
    manual_annotation_allowed: bool
    manual_label_review_allowed: bool
    track_a_dependency_on_nlp_success: bool
    model_training_performed_in_f8: bool
    external_api_called_by_contract_audit: bool
    deploy_in_f8: bool

    @model_validator(mode="after")
    def validate_f8_boundaries(self) -> FinancialNlpIntelligenceConfig:
        expected_model = f"{DEFAULT_MODEL_ID}@{DEFAULT_MODEL_REVISION}"
        configured_model = (
            f"{self.english_sentiment.get('model_id')}@"
            f"{self.english_sentiment.get('model_revision')}"
        )
        if configured_model != expected_model:
            raise ValueError("F8 must use the pinned English FinBERT model revision")
        if self.taiwan_sentiment.get("status") != "UNSUPPORTED_ABSTAIN":
            raise ValueError("unvalidated Taiwan sentiment must abstain")
        if not self.taiwan_sentiment.get("probabilities_must_be_null"):
            raise ValueError("Taiwan sentiment probabilities must be null")
        if self.eland.get("status") != "HOLD_EXCLUDED_FROM_ACTIVE_MODELING":
            raise ValueError("Eland must remain HOLD and excluded")
        if self.eland.get("allowed_role") != "HISTORICAL_REJECTION_EVIDENCE_ONLY":
            raise ValueError("Eland may only be retained as historical rejection evidence")
        prohibited_eland_uses = {
            "training",
            "domain_adaptation",
            "weak_supervision",
            "evaluation",
            "ground_truth",
            "feature_construction",
            "corpus_merge",
            "active_reaudit",
        }
        if set(self.eland.get("prohibited_uses", [])) != prohibited_eland_uses:
            raise ValueError("Eland prohibited uses must remain complete")
        forbidden_flags = (
            self.manual_annotation_allowed,
            self.manual_label_review_allowed,
            self.track_a_dependency_on_nlp_success,
            self.model_training_performed_in_f8,
            self.external_api_called_by_contract_audit,
            self.deploy_in_f8,
        )
        if any(forbidden_flags):
            raise ValueError("F8 boundary flags must remain false")
        return self

    @property
    def english_model_version(self) -> str:
        return (
            f"{self.english_sentiment['model_id']}@"
            f"{self.english_sentiment['model_revision']}"
        )

    @property
    def canonical_sha256(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def load_financial_nlp_intelligence_config(
    path: Path,
) -> FinancialNlpIntelligenceConfig:
    return FinancialNlpIntelligenceConfig.model_validate_json(path.read_text(encoding="utf-8"))


def verify_historical_evidence(
    config: FinancialNlpIntelligenceConfig, *, repository_root: Path
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for relative_path, expected_sha256 in sorted(config.historical_evidence_files.items()):
        path = repository_root / relative_path
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        results.append(
            {
                "path": relative_path,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "passed": actual_sha256 == expected_sha256,
            }
        )
    return results


def assemble_intelligence_item(
    config: FinancialNlpIntelligenceConfig,
    item: NewsItem,
    ticker_matches: list[TickerMatch],
    *,
    sentiment_prediction: SentimentPrediction | None = None,
    sentiment_model_version: str | None = None,
) -> dict[str, object]:
    """Build one safe intelligence record without API calls or model inference."""

    language = item.language.strip().casefold()
    is_english = language == "en" or language.startswith("en-")
    is_chinese = language == "zh" or language.startswith("zh-")
    if sentiment_prediction is not None and not is_english:
        raise ValueError("sentiment predictions are only accepted for supported English text")
    if sentiment_prediction is not None and sentiment_model_version != config.english_model_version:
        raise ValueError("sentiment prediction must use the pinned FinBERT model revision")
    if sentiment_prediction is None and sentiment_model_version is not None:
        raise ValueError("model version cannot be supplied without a sentiment prediction")

    text = build_sentiment_text(item.title, item.summary)
    vote = deterministic_rule_vote(text)
    sentiment = _sentiment_payload(
        config,
        is_english=is_english,
        is_chinese=is_chinese,
        text=text,
        prediction=sentiment_prediction,
        model_version=sentiment_model_version,
    )
    item_identity = item.external_id or "|".join(
        (item.source, item.published_at.isoformat(), item.url, item.title)
    )
    record: dict[str, object] = {
        "schema_version": config.intelligence_version,
        "item_id": hashlib.sha256(item_identity.encode()).hexdigest(),
        "source": item.source,
        "source_type": item.source_type,
        "published_at": item.published_at.isoformat(),
        "language": item.language,
        "ticker_matches": [
            {
                "ticker": match.ticker,
                "relevance_score": match.relevance_score,
                "match_method": match.match_method,
            }
            for match in sorted(ticker_matches, key=lambda value: value.ticker)
        ],
        "sentiment": sentiment,
        "official_metadata": {
            key: item.metadata.get(key) for key in ("company_name", "clause", "fact_date")
        },
        "event_intelligence": {
            "status": "SIGNAL" if vote.abstention_reason is None else "ABSTAIN",
            "normalized_event_type": (
                str(vote.normalized_event_type) if vote.normalized_event_type else None
            ),
            "impact_proxy": str(vote.impact_label) if vote.impact_label else None,
            "confidence": vote.confidence,
            "abstention_reason": vote.abstention_reason,
            "rule_revision": RULE_REVISION,
            "sentiment_ground_truth": False,
            "manual_review_used": False,
        },
        "deterministic_cue_terms": _matched_cue_terms(text),
        "source_excerpt": _bounded_excerpt(item.summary),
        "generated_summary": None,
        "lineage": {
            "external_id": item.external_id,
            "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "config_sha256": config.canonical_sha256,
            "sentiment_model_version": sentiment_model_version,
        },
        "claim_boundary": {
            "chinese_sentiment_validated": False,
            "event_proxy_is_sentiment_ground_truth": False,
            "llm_generated": False,
            "track_a_dependency": False,
        },
    }
    expected_fields = set(config.output_contract["required_fields"])
    if set(record) != expected_fields:
        raise ValueError("assembled record does not match the frozen output contract")
    return record


def _sentiment_payload(
    config: FinancialNlpIntelligenceConfig,
    *,
    is_english: bool,
    is_chinese: bool,
    text: str,
    prediction: SentimentPrediction | None,
    model_version: str | None,
) -> dict[str, object]:
    empty = {
        "label": None,
        "positive_probability": None,
        "neutral_probability": None,
        "negative_probability": None,
        "score": None,
    }
    if is_english and prediction is not None:
        return {
            "status": "SCORED",
            "output_type": "ENGLISH_FINANCIAL_POLARITY",
            **empty,
            "label": prediction.label,
            "positive_probability": prediction.positive_prob,
            "neutral_probability": prediction.neutral_prob,
            "negative_probability": prediction.negative_prob,
            "score": prediction.score,
            "model_version": model_version,
            "input_hash": sentiment_input_hash(text, model_version or ""),
            "abstention_reason": None,
        }
    if is_english:
        return {
            "status": "ELIGIBLE_NOT_SCORED",
            "output_type": "ENGLISH_FINANCIAL_POLARITY",
            **empty,
            "model_version": config.english_model_version,
            "input_hash": None,
            "abstention_reason": "OPTIONAL_MODEL_NOT_RUN",
        }
    return {
        "status": "ABSTAIN",
        "output_type": None,
        **empty,
        "model_version": None,
        "input_hash": None,
        "abstention_reason": (
            config.taiwan_sentiment["abstention_reason"]
            if is_chinese
            else "UNSUPPORTED_LANGUAGE"
        ),
    }


def _matched_cue_terms(text: str) -> list[str]:
    candidates = {
        term for terms in EVENT_TERMS.values() for term in terms
    } | set(POSITIVE_TERMS) | set(NEGATIVE_TERMS)
    return sorted(term for term in candidates if term in text)


def _bounded_excerpt(value: str | None, limit: int = 500) -> str | None:
    normalized = " ".join((value or "").split())
    return normalized[:limit] or None


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
