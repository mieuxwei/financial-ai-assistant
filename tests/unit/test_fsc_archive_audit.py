import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from research.evaluation.fsc_archive_audit import ArchiveSnapshot, audit_archives

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


def _build_archive(path: Path, *, xml_name: str = "本會.xml") -> tuple[int, str]:
    forbidden_text = "不得出現在稽核報告的法規原文"
    fields = {
        "法規類別": "命令",
        "法規體系": "測試",
        "公發布日": "115.08.26",
        "修正日期": "2026-08-26",
        "發文字號": "測字第零號",
        "異動性質": "訂定",
        "生效狀態": "生效",
        "生效日期": "1150826",
        "法規名稱": "測試法規",
        "主旨": "",
        "法規沿革": "",
        "法規內容": forbidden_text,
        "立法理由": "",
        "圖表附件": "",
        "系統異動時間": "2026/08/26 12:00:00",
    }
    xml = io.StringIO()
    xml.write("<LAWS><Law>")
    for field in SCHEMA:
        xml.write(f"<{field}>{fields[field]}</{field}>")
    xml.write("</Law></LAWS>")
    schema = "name,title\n" + "\n".join(f"{field},field" for field in SCHEMA) + "\n"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(xml_name, xml.getvalue().encode())
        archive.writestr("schema.csv", schema.encode("utf-8-sig"))
        archive.writestr("manifest.csv", f"name\n{xml_name}\n".encode("utf-8-sig"))
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


def test_archive_audit_passes_without_emitting_raw_text(tmp_path: Path) -> None:
    size, digest = _build_archive(tmp_path / "commission.zip")
    report = audit_archives(
        _snapshot(size, digest),
        tmp_path,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert report["overall_passed"] is True
    assert report["record_count"] == 1
    assert report["raw_content_stored"] is False
    assert report["manual_labels_used"] is False
    assert "不得出現在稽核報告的法規原文" not in json.dumps(report, ensure_ascii=False)
    observation = report["observations"][0]
    assert observation["xml_root"] == "LAWS"
    assert observation["date_quality"]["公發布日"]["min_date"] == "2026-08-26"


def test_archive_audit_rejects_snapshot_mismatch(tmp_path: Path) -> None:
    size, digest = _build_archive(tmp_path / "commission.zip")
    report = audit_archives(_snapshot(size + 1, digest), tmp_path)

    assert report["overall_passed"] is False
    assert "archive_size_mismatch" in report["observations"][0]["issues"]


def test_archive_audit_rejects_unsafe_member_path(tmp_path: Path) -> None:
    size, digest = _build_archive(tmp_path / "commission.zip", xml_name="../unsafe.xml")
    report = audit_archives(_snapshot(size, digest), tmp_path)

    assert report["overall_passed"] is False
    assert "unsafe_member_path" in report["observations"][0]["issues"]
