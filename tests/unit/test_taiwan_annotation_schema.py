import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.annotation.schema import (
    AnnotationRecord,
    EventType,
    ImpactLabel,
    ReviewStatus,
)


def _record(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sample_id": "twse-2330-20260826-1",
        "source_name": "TWSE",
        "source_type": "material_announcement",
        "source_url": "https://example.com/announcement/1",
        "source_record_id": "announcement-1",
        "published_at": "2026-08-26T09:00:00+08:00",
        "ticker": "2330",
        "entity_name": "範例公司",
        "title": "範例公司公告董事會決議分配股利",
        "text_sha256": "a" * 64,
        "split_group_id": "twse-2330-event-1",
        "event_type": "DIVIDEND",
        "impact_label": "NEUTRAL",
        "confidence": 3,
        "annotator_id": "reviewer-01",
        "review_status": "REVIEWED",
        "include_for_training": True,
    }
    payload.update(overrides)
    return payload


def test_reviewed_annotation_can_be_included_for_training() -> None:
    record = AnnotationRecord.model_validate(_record())

    assert record.event_type is EventType.DIVIDEND
    assert record.impact_label is ImpactLabel.NEUTRAL
    assert record.review_status is ReviewStatus.REVIEWED
    assert record.include_for_training is True


def test_ambiguous_annotation_requires_reason() -> None:
    with pytest.raises(ValidationError, match="AMBIGUOUS requires ambiguous_reason"):
        AnnotationRecord.model_validate(_record(impact_label="AMBIGUOUS"))


def test_draft_annotation_cannot_be_training_data() -> None:
    with pytest.raises(ValidationError, match="training records must be reviewed"):
        AnnotationRecord.model_validate(_record(review_status="DRAFT"))


def test_schema_rejects_unknown_version() -> None:
    with pytest.raises(ValidationError):
        AnnotationRecord.model_validate(_record(schema_version="v2"))


def test_taxonomy_file_matches_schema_enums() -> None:
    taxonomy_path = Path(__file__).parents[2] / "research/configs/taiwan_event_taxonomy.v1.json"
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))

    assert {item["code"] for item in taxonomy["event_types"]} == {item.value for item in EventType}
    assert {item["code"] for item in taxonomy["impact_labels"]} == {
        item.value for item in ImpactLabel
    }
