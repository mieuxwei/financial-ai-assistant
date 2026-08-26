from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewerAnnotation:
    candidate_id: str
    event_type: str
    impact_label: str
    confidence: int
    review_status: str
    ambiguous_reason: str | None = None
    exclusion_reason: str | None = None


def cohens_kappa(left: list[str], right: list[str]) -> float | None:
    if len(left) != len(right):
        raise ValueError("label vectors must have equal length")
    if not left:
        return None
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    labels = left_counts.keys() | right_counts.keys()
    expected = sum(
        (left_counts[label] / len(left)) * (right_counts[label] / len(right)) for label in labels
    )
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def build_agreement_report(
    reviewer_a: Iterable[ReviewerAnnotation],
    reviewer_b: Iterable[ReviewerAnnotation],
    *,
    minimum_kappa: float = 0.60,
) -> dict[str, object]:
    if not 0.0 <= minimum_kappa <= 1.0:
        raise ValueError("minimum_kappa must be between 0 and 1")
    left = _index(reviewer_a)
    right = _index(reviewer_b)
    if left.keys() != right.keys():
        missing_from_a = sorted(right.keys() - left.keys())
        missing_from_b = sorted(left.keys() - right.keys())
        raise ValueError(
            f"reviewer candidate sets differ: missing_from_a={missing_from_a}, "
            f"missing_from_b={missing_from_b}"
        )

    candidate_ids = sorted(left)
    included_ids = [
        candidate_id
        for candidate_id in candidate_ids
        if left[candidate_id].review_status != "EXCLUDED"
        and right[candidate_id].review_status != "EXCLUDED"
    ]
    event_left = [left[candidate_id].event_type for candidate_id in included_ids]
    event_right = [right[candidate_id].event_type for candidate_id in included_ids]
    impact_left = [left[candidate_id].impact_label for candidate_id in included_ids]
    impact_right = [right[candidate_id].impact_label for candidate_id in included_ids]
    event_kappa = cohens_kappa(event_left, event_right)
    impact_kappa = cohens_kappa(impact_left, impact_right)
    event_conflicts = [
        candidate_id
        for candidate_id in included_ids
        if left[candidate_id].event_type != right[candidate_id].event_type
    ]
    impact_conflicts = [
        candidate_id
        for candidate_id in included_ids
        if left[candidate_id].impact_label != right[candidate_id].impact_label
    ]
    exclusion_conflicts = [
        candidate_id
        for candidate_id in candidate_ids
        if (left[candidate_id].review_status == "EXCLUDED")
        != (right[candidate_id].review_status == "EXCLUDED")
    ]
    passed = (
        event_kappa is not None
        and impact_kappa is not None
        and event_kappa >= minimum_kappa
        and impact_kappa >= minimum_kappa
    )
    return {
        "report_schema_version": "taiwan-annotation-agreement-v1",
        "candidate_count": len(candidate_ids),
        "jointly_included_count": len(included_ids),
        "minimum_kappa": minimum_kappa,
        "event": _metric(event_left, event_right, event_kappa, event_conflicts),
        "impact": _metric(impact_left, impact_right, impact_kappa, impact_conflicts),
        "exclusion_conflict_count": len(exclusion_conflicts),
        "exclusion_conflict_candidate_ids": exclusion_conflicts,
        "passed_calibration_gate": passed,
        "decision": "PROCEED_TO_ADJUDICATION" if passed else "PAUSE_AND_REVISE_GUIDELINE",
        "contains_raw_text": False,
    }


def _index(rows: Iterable[ReviewerAnnotation]) -> dict[str, ReviewerAnnotation]:
    output = {}
    for row in rows:
        if not row.candidate_id:
            raise ValueError("candidate_id is required")
        if row.candidate_id in output:
            raise ValueError(f"duplicate candidate_id: {row.candidate_id}")
        if not row.event_type or not row.impact_label:
            raise ValueError(f"incomplete labels for candidate_id: {row.candidate_id}")
        if row.confidence not in {1, 2, 3}:
            raise ValueError(f"invalid confidence for candidate_id: {row.candidate_id}")
        if row.review_status not in {"REVIEWED", "EXCLUDED"}:
            raise ValueError(f"invalid review_status for candidate_id: {row.candidate_id}")
        if row.impact_label == "AMBIGUOUS" and not row.ambiguous_reason:
            raise ValueError(f"AMBIGUOUS requires reason for candidate_id: {row.candidate_id}")
        if row.review_status == "EXCLUDED" and not row.exclusion_reason:
            raise ValueError(f"EXCLUDED requires reason for candidate_id: {row.candidate_id}")
        output[row.candidate_id] = row
    return output


def _metric(
    left: list[str],
    right: list[str],
    kappa: float | None,
    conflicts: list[str],
) -> dict[str, object]:
    count = len(left)
    return {
        "evaluated_count": count,
        "raw_agreement": (
            round(sum(a == b for a, b in zip(left, right, strict=True)) / count, 6)
            if count
            else None
        ),
        "cohens_kappa": round(kappa, 6) if kappa is not None else None,
        "conflict_count": len(conflicts),
        "conflict_candidate_ids": conflicts,
        "disagreement_pair_distribution": _disagreement_pairs(left, right),
        "reviewer_a_distribution": dict(sorted(Counter(left).items())),
        "reviewer_b_distribution": dict(sorted(Counter(right).items())),
    }


def _disagreement_pairs(left: list[str], right: list[str]) -> dict[str, int]:
    pairs = Counter(
        f"{a} -> {b}"
        for a, b in zip(left, right, strict=True)
        if a != b
    )
    return dict(sorted(pairs.items()))
