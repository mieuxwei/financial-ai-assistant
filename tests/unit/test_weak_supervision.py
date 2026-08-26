import hashlib

import pytest

from research.annotation.schema import EventType, ImpactLabel
from research.weak_supervision.aggregation import aggregate_weak_votes
from research.weak_supervision.deterministic import deterministic_rule_vote
from research.weak_supervision.schema import WeakAggregationConfig, WeakVote


def _config() -> WeakAggregationConfig:
    return WeakAggregationConfig.model_validate(
        {
            "minimum_sources": 2,
            "minimum_margin": 0.2,
            "labeling_function_weights": {
                "deterministic_rules": 1.0,
                "official_category_map": 1.0,
                "local_frozen_model": 0.75,
            },
        }
    )


def _vote(function_id: str, label: ImpactLabel, confidence: float = 0.8) -> WeakVote:
    return WeakVote(
        labeling_function_id=function_id,
        labeling_function_revision=f"{function_id}-v1",
        source_type=(
            "local_model" if function_id == "local_frozen_model" else "official_category"
        ),
        impact_label=label,
        normalized_event_type=EventType.REVENUE,
        confidence=confidence,
        input_sha256="a" * 64,
        model_version="model@revision" if function_id == "local_frozen_model" else None,
    )


def test_weighted_consensus_keeps_official_and_inferred_categories_separate() -> None:
    result = aggregate_weak_votes(
        [
            _vote("official_category_map", ImpactLabel.POSITIVE),
            _vote("local_frozen_model", ImpactLabel.POSITIVE),
        ],
        _config(),
        official_source_category="官方條款-31",
    )

    assert result["official_source_category"] == "官方條款-31"
    assert result["normalized_event_type"] == "REVENUE"
    assert result["weak_label"] == "POSITIVE"
    assert result["impact_abstention_reason"] is None
    assert result["manual_labels_used"] is False
    assert result["sentiment_ground_truth"] is False
    assert len(result["vote_snapshot_sha256"]) == 64


def test_conflict_becomes_ambiguous_without_adjudication() -> None:
    result = aggregate_weak_votes(
        [
            _vote("official_category_map", ImpactLabel.POSITIVE),
            _vote("deterministic_rules", ImpactLabel.NEGATIVE),
        ],
        _config(),
    )

    assert result["weak_label"] == "AMBIGUOUS"
    assert result["impact_abstention_reason"] == "VOTE_CONFLICT"
    assert result["agreement"] == 0.5
    assert result["vote_entropy"] == pytest.approx(1.0)
    assert result["manual_review_used"] is False


def test_insufficient_sources_abstain_and_input_hashes_must_match() -> None:
    result = aggregate_weak_votes(
        [_vote("official_category_map", ImpactLabel.NEUTRAL)], _config()
    )
    assert result["weak_label"] is None
    assert result["impact_abstention_reason"] == "INSUFFICIENT_INDEPENDENT_SOURCES"

    mismatched = _vote("local_frozen_model", ImpactLabel.NEUTRAL).model_copy(
        update={"input_sha256": "b" * 64}
    )
    with pytest.raises(ValueError, match="same normalized input"):
        aggregate_weak_votes(
            [_vote("official_category_map", ImpactLabel.NEUTRAL), mismatched], _config()
        )


def test_deterministic_rules_are_conservative_and_hash_input_only() -> None:
    positive = deterministic_rule_vote("公司月營收成長並取得重大訂單")
    conflict = deterministic_rule_vote("月營收成長，但本期獲利減少")
    missing = deterministic_rule_vote("依規定補充說明相關資訊")

    assert positive.normalized_event_type is EventType.REVENUE
    assert positive.impact_label is ImpactLabel.POSITIVE
    assert positive.input_sha256 == hashlib.sha256(
        "公司月營收成長並取得重大訂單".encode()
    ).hexdigest()
    assert conflict.impact_label is ImpactLabel.AMBIGUOUS
    assert missing.impact_label is None
    assert missing.abstention_reason == "NO_RULE_MATCH"
    assert missing.confidence == 0


def test_signal_vote_requires_positive_confidence() -> None:
    with pytest.raises(ValueError, match="positive confidence"):
        WeakVote(
            labeling_function_id="official_category_map",
            labeling_function_revision="v1",
            source_type="official_category",
            impact_label=ImpactLabel.NEUTRAL,
            confidence=0,
            input_sha256="a" * 64,
        )
