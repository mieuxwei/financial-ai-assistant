import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from research.evaluation.fsc_archive_audit import ArchiveSnapshot
from research.training.fsc_corpus import (
    CorpusConfig,
    _require_safe_raw_output,
    build_corpus,
)

SCHEMA = [
    "法規類別",
    "法規體系",
    "公發布日",
    "修正日期",
    "發文字號",
    "異動性質",
    "生效狀態",
    "生效日期",
    "法規名稱",
    "主旨",
    "法規沿革",
    "法規內容",
    "立法理由",
    "圖表附件",
    "系統異動時間",
]


def _law(**overrides: str) -> dict[str, str]:
    fields = {field: "" for field in SCHEMA}
    fields.update(
        {
            "法規類別": "命令",
            "法規體系": "金融",
            "公發布日": "2022-01-01",
            "修正日期": "2022-01-01",
            "發文字號": "測字第一號",
            "法規名稱": "預設法規",
            "法規內容": "預設內容",
        }
    )
    fields.update(overrides)
    return fields


def _archive(path: Path) -> tuple[int, str]:
    rows = [
        _law(法規名稱="跨期法規", 法規內容="舊版內容", 公發布日="2022-01-01"),
        _law(法規名稱="跨期法規", 法規內容="新版內容", 公發布日="2025-01-01"),
        _law(法規名稱="驗證法規", 法規內容="驗證內容", 公發布日="2023-01-01"),
        _law(法規名稱="訓練法規", 法規內容="訓練內容", 公發布日="2021-01-01"),
        _law(法規名稱="重複法規", 法規內容="訓練內容", 公發布日="2022-02-01"),
        _law(法規名稱="錯誤日期", 法規內容="日期錯誤內容", 公發布日="unknown"),
        _law(法規名稱="空白內容", 法規內容="", 公發布日="2020-01-01"),
    ]
    xml_parts = ["<LAWS>"]
    for row in rows:
        xml_parts.append("<Law>")
        xml_parts.extend(f"<{field}>{row[field]}</{field}>" for field in SCHEMA)
        xml_parts.append("</Law>")
    xml_parts.append("</LAWS>")
    schema = "name,title\n" + "\n".join(f"{field},field" for field in SCHEMA) + "\n"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("本會.xml", "".join(xml_parts).encode())
        archive.writestr("schema.csv", schema.encode("utf-8-sig"))
        archive.writestr("manifest.csv", "name\n本會.xml\n".encode("utf-8-sig"))
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


def _snapshot(size: int, digest: str) -> ArchiveSnapshot:
    return ArchiveSnapshot.model_validate(
        {
            "expected_schema_fields": SCHEMA,
            "archives": [
                {
                    "source_id": "fsc_test_archive",
                    "agency": "commission",
                    "local_filename": "commission.zip",
                    "source_url": "https://example.test/commission.zip",
                    "expected_size_bytes": size,
                    "expected_sha256": digest,
                }
            ],
        }
    )


def _config() -> CorpusConfig:
    return CorpusConfig.model_validate(
        {
            "train_end": "2022-12-31",
            "validation_end": "2024-12-31",
            "family_field_priority": ["法規名稱", "主旨", "發文字號"],
            "text_field": "法規內容",
            "publication_date_field": "公發布日",
            "revision_date_field": "修正日期",
            "allowed_use": "unlabelled feasibility",
            "forbidden_uses": ["sentiment truth"],
        }
    )


def test_builder_filters_deduplicates_and_isolates_families(tmp_path: Path) -> None:
    size, digest = _archive(tmp_path / "commission.zip")
    output = tmp_path / "output"
    report = build_corpus(
        _config(),
        _snapshot(size, digest),
        tmp_path,
        output,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert report["input_record_count"] == 7
    assert report["retained_record_count"] == 4
    assert report["exclusion_counts"] == {
        "duplicate_content": 1,
        "empty_content": 1,
        "invalid_publication_date": 1,
    }
    assert {name: data["record_count"] for name, data in report["split_files"].items()} == {
        "test": 2,
        "train": 1,
        "validation": 1,
    }
    test_rows = [json.loads(line) for line in (output / "test.jsonl").read_text().splitlines()]
    assert len({row["family_sha256"] for row in test_rows}) == 1
    assert "舊版內容" not in json.dumps(report, ensure_ascii=False)
    assert report["manual_labels_used"] is False
    assert report["sentiment_ground_truth"] is False


def test_builder_is_reproducible_and_does_not_overwrite(tmp_path: Path) -> None:
    size, digest = _archive(tmp_path / "commission.zip")
    output = tmp_path / "output"
    first = build_corpus(
        _config(), _snapshot(size, digest), tmp_path, output, generated_at=datetime.now(UTC)
    )
    second = build_corpus(
        _config(),
        _snapshot(size, digest),
        tmp_path,
        output,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert first["corpus_sha256"] == second["corpus_sha256"]


def test_cli_output_guard_rejects_nonignored_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside .tools"):
        _require_safe_raw_output(tmp_path / "public-corpus")
