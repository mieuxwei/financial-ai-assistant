from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from research.annotation.calibration_batch import (
    AnnouncementCandidate,
    build_calibration_batch,
    ensure_private_output_path,
)


def _candidate(
    ticker: str,
    title: str,
    *,
    offset: int,
    fingerprint: str | None = None,
    source: str = "twse_material",
) -> AnnouncementCandidate:
    return AnnouncementCandidate(
        source=source,
        source_type="official_announcement",
        source_url="https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
        source_record_id=f"record-{ticker}-{offset}",
        published_at=datetime(2026, 8, 1, tzinfo=UTC) + timedelta(days=offset),
        ticker=ticker,
        entity_name=f"公司{ticker}",
        title=title,
        context="只包含發布當下可見的公告短說明。",
        content_hash=f"content-{ticker}-{offset}",
        title_fingerprint=fingerprint or f"title-{ticker}-{offset}",
    )


def test_batch_is_unlabeled_balanced_and_excludes_frozen_text() -> None:
    frozen = "這筆文字屬於既有凍結診斷集"
    candidates = [
        _candidate("2330", frozen, offset=0),
        _candidate("2330", "甲公司第一筆公告", offset=1),
        _candidate("2330", "甲公司第二筆公告", offset=2),
        _candidate("2317", "乙公司第一筆公告", offset=3),
        _candidate("2317", "乙公司第二筆公告", offset=4),
        _candidate("9999", "非官方來源", offset=5, source="other"),
    ]

    rows = build_calibration_batch(candidates, limit=3, excluded_texts=[frozen])

    assert [row["ticker"] for row in rows] == ["2317", "2330", "2317"]
    assert all(row["impact_label"] is None for row in rows)
    assert all(row["event_type"] is None for row in rows)
    assert all(row["include_for_training"] is False for row in rows)
    assert all("return" not in key for row in rows for key in row)
    assert frozen not in {row["title"] for row in rows}


def test_batch_deduplicates_title_fingerprint() -> None:
    rows = build_calibration_batch(
        [
            _candidate("2330", "公告原文", offset=0, fingerprint="same"),
            _candidate("2317", "公告近似改寫", offset=1, fingerprint="same"),
        ],
        limit=5,
    )

    assert len(rows) == 1


def test_private_output_path_rejects_tracked_location(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must stay under"):
        ensure_private_output_path(Path("calibration.jsonl"), cwd=tmp_path)

    accepted = ensure_private_output_path(Path("artifacts/calibration.jsonl"), cwd=tmp_path)
    assert accepted == tmp_path / "artifacts/calibration.jsonl"
