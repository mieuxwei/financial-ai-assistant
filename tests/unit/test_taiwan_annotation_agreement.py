import pytest

from research.annotation.agreement import (
    ReviewerAnnotation,
    build_agreement_report,
    cohens_kappa,
)


def _row(
    candidate_id: str,
    event_type: str,
    impact_label: str,
    *,
    review_status: str = "REVIEWED",
) -> ReviewerAnnotation:
    return ReviewerAnnotation(
        candidate_id=candidate_id,
        event_type=event_type,
        impact_label=impact_label,
        confidence=3,
        review_status=review_status,
        ambiguous_reason="direction is not resolved" if impact_label == "AMBIGUOUS" else None,
        exclusion_reason="not eligible" if review_status == "EXCLUDED" else None,
    )


def test_kappa_is_one_for_identical_labels() -> None:
    assert cohens_kappa(["A", "B", "A"], ["A", "B", "A"]) == 1.0


def test_agreement_report_contains_ids_but_no_raw_text() -> None:
    reviewer_a = [
        _row("id-1", "EARNINGS", "POSITIVE"),
        _row("id-2", "DIVIDEND", "NEUTRAL"),
        _row("id-3", "BUYBACK", "POSITIVE"),
    ]
    reviewer_b = [
        _row("id-1", "EARNINGS", "POSITIVE"),
        _row("id-2", "DIVIDEND", "AMBIGUOUS"),
        _row("id-3", "BUYBACK", "POSITIVE"),
    ]

    report = build_agreement_report(reviewer_a, reviewer_b, minimum_kappa=0.60)

    assert report["candidate_count"] == 3
    assert report["event"]["cohens_kappa"] == 1.0
    assert report["impact"]["conflict_candidate_ids"] == ["id-2"]
    assert report["impact"]["disagreement_pair_distribution"] == {
        "NEUTRAL -> AMBIGUOUS": 1
    }
    assert report["contains_raw_text"] is False


def test_excluded_rows_are_not_used_for_label_kappa() -> None:
    reviewer_a = [
        _row("id-1", "EARNINGS", "POSITIVE"),
        _row("id-2", "OTHER", "AMBIGUOUS", review_status="EXCLUDED"),
    ]
    reviewer_b = [
        _row("id-1", "EARNINGS", "POSITIVE"),
        _row("id-2", "REGULATORY", "NEGATIVE"),
    ]

    report = build_agreement_report(reviewer_a, reviewer_b)

    assert report["jointly_included_count"] == 1
    assert report["exclusion_conflict_candidate_ids"] == ["id-2"]
    assert report["event"]["cohens_kappa"] == 1.0


def test_reviewer_candidate_sets_must_match() -> None:
    with pytest.raises(ValueError, match="candidate sets differ"):
        build_agreement_report(
            [_row("id-1", "EARNINGS", "POSITIVE")],
            [_row("id-2", "EARNINGS", "POSITIVE")],
        )


def test_ambiguous_and_excluded_rows_require_reasons() -> None:
    with pytest.raises(ValueError, match="AMBIGUOUS requires reason"):
        build_agreement_report(
            [
                ReviewerAnnotation(
                    candidate_id="id-1",
                    event_type="OTHER",
                    impact_label="AMBIGUOUS",
                    confidence=2,
                    review_status="REVIEWED",
                )
            ],
            [_row("id-1", "OTHER", "AMBIGUOUS")],
        )

    with pytest.raises(ValueError, match="EXCLUDED requires reason"):
        build_agreement_report(
            [
                ReviewerAnnotation(
                    candidate_id="id-1",
                    event_type="OTHER",
                    impact_label="NEUTRAL",
                    confidence=2,
                    review_status="EXCLUDED",
                )
            ],
            [_row("id-1", "OTHER", "NEUTRAL", review_status="EXCLUDED")],
        )
