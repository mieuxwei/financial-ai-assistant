from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from enum import StrEnum

from research.annotation.schema import ImpactLabel
from research.weak_supervision.schema import WeakAggregationConfig, WeakVote


def aggregate_weak_votes(
    votes: list[WeakVote],
    config: WeakAggregationConfig,
    *,
    official_source_category: str | None = None,
) -> dict[str, object]:
    if not votes:
        raise ValueError("at least one weak vote is required")
    function_ids = [vote.labeling_function_id for vote in votes]
    if len(function_ids) != len(set(function_ids)):
        raise ValueError("labeling functions must vote at most once per input")
    unknown = sorted(set(function_ids) - set(config.labeling_function_weights))
    if unknown:
        raise ValueError(f"unconfigured labeling functions: {', '.join(unknown)}")
    input_hashes = {vote.input_sha256 for vote in votes}
    if len(input_hashes) != 1:
        raise ValueError("all votes must refer to the same normalized input")

    impact_votes = [vote for vote in votes if vote.impact_label is not None]
    event_votes = [vote for vote in votes if vote.normalized_event_type is not None]
    impact = _aggregate_concept(
        impact_votes,
        config,
        value_getter=lambda vote: vote.impact_label,
        ambiguous_value=ImpactLabel.AMBIGUOUS,
    )
    event = _aggregate_concept(
        event_votes,
        config,
        value_getter=lambda vote: vote.normalized_event_type,
        ambiguous_value=None,
    )
    canonical_votes = [
        vote.model_dump(mode="json")
        for vote in sorted(votes, key=lambda item: item.labeling_function_id)
    ]
    snapshot_payload = {
        "protocol_version": config.protocol_version,
        "minimum_sources": config.minimum_sources,
        "minimum_margin": config.minimum_margin,
        "weights": dict(sorted(config.labeling_function_weights.items())),
        "votes": canonical_votes,
    }
    snapshot = json.dumps(
        snapshot_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "protocol_version": config.protocol_version,
        "official_source_category": official_source_category,
        "normalized_event_type": event["value"],
        "event_confidence": event["confidence"],
        "event_abstention_reason": event["reason"],
        "weak_label": impact["value"],
        "weak_confidence": impact["confidence"],
        "impact_abstention_reason": impact["reason"],
        "coverage": len(impact_votes) / len(votes),
        "agreement": impact["agreement"],
        "vote_entropy": impact["entropy"],
        "vote_count": len(votes),
        "impact_vote_count": len(impact_votes),
        "event_vote_count": len(event_votes),
        "abstained_vote_count": sum(
            vote.impact_label is None and vote.normalized_event_type is None for vote in votes
        ),
        "labeling_function_versions": {
            vote.labeling_function_id: vote.labeling_function_revision
            for vote in sorted(votes, key=lambda item: item.labeling_function_id)
        },
        "model_versions": sorted(
            {vote.model_version for vote in votes if vote.model_version is not None}
        ),
        "prompt_hashes": sorted(
            {vote.prompt_sha256 for vote in votes if vote.prompt_sha256 is not None}
        ),
        "input_sha256": next(iter(input_hashes)),
        "vote_snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "manual_labels_used": False,
        "manual_review_used": False,
        "sentiment_ground_truth": False,
    }


def _aggregate_concept(
    votes: list[WeakVote],
    config: WeakAggregationConfig,
    *,
    value_getter: Callable[[WeakVote], StrEnum | None],
    ambiguous_value: StrEnum | None,
) -> dict[str, object]:
    if len(votes) < config.minimum_sources:
        return {
            "value": None,
            "confidence": 0.0,
            "agreement": 0.0,
            "entropy": 0.0,
            "reason": "INSUFFICIENT_INDEPENDENT_SOURCES",
        }
    scores: dict[StrEnum, float] = defaultdict(float)
    counts: Counter[StrEnum] = Counter()
    for vote in votes:
        value = value_getter(vote)
        if value is None:
            continue
        scores[value] += (
            config.labeling_function_weights[vote.labeling_function_id] * vote.confidence
        )
        counts[value] += 1
    ordered = sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
    total_score = sum(scores.values())
    winner, winner_score = ordered[0]
    runner_score = ordered[1][1] if len(ordered) > 1 else 0.0
    margin = (winner_score - runner_score) / total_score if total_score else 0.0
    agreement = max(counts.values()) / sum(counts.values())
    entropy = _normalized_entropy(list(scores.values()))
    if margin < config.minimum_margin:
        return {
            "value": str(ambiguous_value) if ambiguous_value is not None else None,
            "confidence": winner_score / total_score if total_score else 0.0,
            "agreement": agreement,
            "entropy": entropy,
            "reason": "VOTE_CONFLICT",
        }
    return {
        "value": str(winner),
        "confidence": winner_score / total_score,
        "agreement": agreement,
        "entropy": entropy,
        "reason": None,
    }


def _normalized_entropy(scores: list[float]) -> float:
    positive = [score for score in scores if score > 0]
    if len(positive) <= 1:
        return 0.0
    total = sum(positive)
    entropy = -sum((score / total) * math.log(score / total) for score in positive)
    return entropy / math.log(len(positive))
