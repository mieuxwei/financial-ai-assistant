import json

import pytest

from research.evaluation.taiwan_dataset_audit import audit_dataset, read_rows


def _row(text: str, label: str = "positive", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "text": text,
        "overall": label,
        "entity": "範例公司",
        "task": "overall",
        "source": "synthetic-test",
        "source_url": "https://example.com/source",
        "published_at": "2026-08-26T09:00:00+08:00",
    }
    row.update(overrides)
    return row


def test_audit_detects_leakage_conflicts_and_omits_raw_text() -> None:
    exact_text = "範例公司公告本月營收成長，內容僅供資料稽核測試使用。"
    near_train = "範例公司公告本月營收成長百分之十，董事會確認目前公司整體營運情況維持正常。"
    near_test = "範例公司公告本月營收成長百分之九，董事會確認目前公司整體營運情況維持正常。"
    split_rows = {
        "train": [
            _row(exact_text, "positive"),
            _row(near_train, "positive"),
            _row("本週星座愛情運與股票完全無關的範例內容。", "unknown"),
        ],
        "test": [
            _row(exact_text, "negative"),
            _row(near_test, "positive", source_url="", published_at=""),
        ],
    }

    report = audit_dataset(
        split_rows,
        dataset_id="synthetic/unit-test",
        dataset_revision="test-revision",
        declared_license="synthetic-only",
        fuzzy_threshold=0.85,
    )

    assert report["row_count"] == 5
    assert report["split_counts"] == {"test": 2, "train": 3}
    assert report["duplicates"]["exact_cross_split_group_count"] == 1
    assert report["duplicates"]["conflicting_label_group_count"] == 1
    assert report["duplicates"]["fuzzy_cross_split_candidate_count"] >= 1
    assert report["missing_traceability"] == {"source_url": 1, "published_at": 1}
    assert report["unknown_effective_labels"] == ["unknown"]
    assert report["automated_screen"]["passed"] is False

    serialized = json.dumps(report, ensure_ascii=False)
    assert exact_text not in serialized
    assert near_train not in serialized
    assert near_test not in serialized


def test_audit_validates_fuzzy_threshold() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        audit_dataset(
            {},
            dataset_id="synthetic/unit-test",
            dataset_revision="test-revision",
            declared_license="synthetic-only",
            fuzzy_threshold=1.01,
        )


def test_read_rows_supports_jsonl(tmp_path) -> None:
    path = tmp_path / "samples.jsonl"
    path.write_text(
        '{"text":"第一筆","overall":"neutral"}\n{"text":"第二筆","overall":"positive"}\n',
        encoding="utf-8",
    )

    rows = read_rows(path)

    assert [row["text"] for row in rows] == ["第一筆", "第二筆"]
