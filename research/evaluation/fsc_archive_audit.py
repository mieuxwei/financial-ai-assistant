from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Literal
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SNAPSHOT_VERSION = "fsc-official-archive-snapshot-v1"
REPORT_VERSION = "fsc-official-archive-audit-v1"
DEFAULT_SNAPSHOT = Path("research/configs/fsc_official_archive_snapshot.v1.json")
DEFAULT_ARCHIVE_DIR = Path(".tools/datasets/fsc-official")
DEFAULT_OUTPUT = Path("artifacts/fsc-official-archive-audit.json")
DATE_FIELDS = ("公發布日", "修正日期", "生效日期", "系統異動時間")
TEXT_FIELDS = ("法規名稱", "主旨", "法規沿革", "法規內容", "立法理由")
IDENTITY_FIELDS = ("發文字號", "法規名稱")
MAX_ARCHIVE_SIZE = 5_000_000
MAX_UNCOMPRESSED_SIZE = 25_000_000
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
DATE_PARTS = re.compile(r"(?<!\d)(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})(?!\d)")
COMPACT_DATE = re.compile(r"(?<!\d)(\d{7,8})(?!\d)")


class ArchiveDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    agency: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    local_filename: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*\.zip$")
    source_url: HttpUrl
    expected_size_bytes: int = Field(ge=1, le=MAX_ARCHIVE_SIZE)
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ArchiveSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    snapshot_version: Literal["fsc-official-archive-snapshot-v1"] = SNAPSHOT_VERSION
    expected_schema_fields: list[str] = Field(min_length=1)
    archives: list[ArchiveDefinition] = Field(min_length=1)

    @field_validator("expected_schema_fields")
    @classmethod
    def validate_schema(cls, value: list[str]) -> list[str]:
        if any(not field for field in value) or len(set(value)) != len(value):
            raise ValueError("expected_schema_fields must be non-empty and unique")
        return value

    @model_validator(mode="after")
    def validate_unique_archives(self) -> ArchiveSnapshot:
        for attribute in ("source_id", "agency", "local_filename"):
            values = [getattr(item, attribute) for item in self.archives]
            if len(values) != len(set(values)):
                raise ValueError(f"archive {attribute} values must be unique")
        return self


def load_snapshot(path: Path) -> ArchiveSnapshot:
    return ArchiveSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def audit_archives(
    snapshot: ArchiveSnapshot,
    archive_dir: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = generated_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")

    observations = []
    all_record_hashes: Counter[str] = Counter()
    all_content_hashes: Counter[str] = Counter()
    record_sources: dict[str, set[str]] = {}
    content_sources: dict[str, set[str]] = {}
    for definition in snapshot.archives:
        observation, record_hashes, content_hashes = _audit_archive(
            definition,
            archive_dir / definition.local_filename,
            snapshot.expected_schema_fields,
        )
        observations.append(observation)
        all_record_hashes.update(record_hashes)
        all_content_hashes.update(content_hashes)
        for digest in record_hashes:
            record_sources.setdefault(digest, set()).add(definition.source_id)
        for digest in content_hashes:
            content_sources.setdefault(digest, set()).add(definition.source_id)

    total_records = sum(int(item["record_count"]) for item in observations)
    return {
        "report_version": REPORT_VERSION,
        "snapshot_version": snapshot.snapshot_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "overall_passed": all(item["structural_passed"] for item in observations),
        "archive_count": len(observations),
        "record_count": total_records,
        "cross_archive_duplicates": {
            "exact_record_groups": _cross_source_group_count(record_sources),
            "content_groups": _cross_source_group_count(content_sources),
            "exact_record_extra_rows": _cross_source_extra_rows(
                all_record_hashes, record_sources
            ),
            "content_extra_rows": _cross_source_extra_rows(
                all_content_hashes, content_sources
            ),
        },
        "observations": observations,
        "raw_content_stored": False,
        "manual_labels_used": False,
        "manual_review_used": False,
    }


def _audit_archive(
    definition: ArchiveDefinition,
    path: Path,
    expected_schema: list[str],
) -> tuple[dict[str, object], Counter[str], Counter[str]]:
    issues: list[str] = []
    record_hashes: Counter[str] = Counter()
    content_hashes: Counter[str] = Counter()
    base: dict[str, object] = {
        "source_id": definition.source_id,
        "agency": definition.agency,
        "source_url": str(definition.source_url),
        "archive_filename": definition.local_filename,
        "expected_size_bytes": definition.expected_size_bytes,
        "expected_sha256": definition.expected_sha256,
        "raw_content_stored": False,
    }
    if not path.is_file():
        return _failed_observation(base, "archive_missing"), record_hashes, content_hashes

    size = path.stat().st_size
    digest = _sha256_file(path)
    if size != definition.expected_size_bytes:
        issues.append("archive_size_mismatch")
    if digest != definition.expected_sha256:
        issues.append("archive_sha256_mismatch")

    try:
        with ZipFile(path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                issues.append("zip_crc_failure")
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if any(not _safe_member_name(info.filename) for info in infos):
                issues.append("unsafe_member_path")
            uncompressed_size = sum(info.file_size for info in infos)
            if uncompressed_size > MAX_UNCOMPRESSED_SIZE:
                issues.append("uncompressed_size_exceeded")
            xml_members = [info for info in infos if info.filename.casefold().endswith(".xml")]
            schema_members = [
                info for info in infos if PurePosixPath(info.filename).name == "schema.csv"
            ]
            manifest_members = [
                info for info in infos if PurePosixPath(info.filename).name == "manifest.csv"
            ]
            if len(infos) != 3 or len(xml_members) != 1:
                issues.append("unexpected_archive_members")
            if len(schema_members) != 1:
                issues.append("missing_or_duplicate_schema")
            if len(manifest_members) != 1:
                issues.append("missing_or_duplicate_manifest")
            if issues:
                return (
                    _failed_observation(
                        base,
                        *issues,
                        archive_size_bytes=size,
                        archive_sha256=digest,
                        member_count=len(infos),
                        uncompressed_size_bytes=uncompressed_size,
                    ),
                    record_hashes,
                    content_hashes,
                )

            schema_rows = _read_csv(archive, schema_members[0].filename)
            manifest_rows = _read_csv(archive, manifest_members[0].filename)
            declared_schema = _schema_fields(schema_rows)
            if declared_schema != expected_schema:
                issues.append("schema_mismatch")
            if not _valid_manifest(manifest_rows):
                issues.append("invalid_manifest")

            xml_result, record_hashes, content_hashes = _audit_xml(
                archive, xml_members[0].filename, expected_schema, definition.agency
            )
            issues.extend(xml_result.pop("issues"))
            return (
                {
                    **base,
                    "structural_passed": not issues,
                    "archive_size_bytes": size,
                    "archive_sha256": digest,
                    "member_count": len(infos),
                    "uncompressed_size_bytes": uncompressed_size,
                    "schema_field_count": len(declared_schema),
                    "schema_sha256": _hash_sequence(declared_schema),
                    **xml_result,
                    "issues": sorted(set(issues)),
                    "error_code": None,
                },
                record_hashes,
                content_hashes,
            )
    except (BadZipFile, ET.ParseError, UnicodeDecodeError, csv.Error, OSError, ValueError) as error:
        return (
            _failed_observation(
                base,
                "archive_audit_failed",
                archive_size_bytes=size,
                archive_sha256=digest,
                error_code=type(error).__name__,
            ),
            record_hashes,
            content_hashes,
        )


def _audit_xml(
    archive: ZipFile,
    member: str,
    expected_schema: list[str],
    agency: str,
) -> tuple[dict[str, object], Counter[str], Counter[str]]:
    record_hashes: Counter[str] = Counter()
    content_hashes: Counter[str] = Counter()
    identity_hashes: Counter[str] = Counter()
    missing_fields: Counter[str] = Counter()
    date_stats = {
        field: {"present": 0, "parsed": 0, "failed": 0, "dates": []}
        for field in DATE_FIELDS
    }
    text_lengths: list[int] = []
    records_with_markup = 0
    records_with_control_characters = 0
    observed_fields: set[str] = set()
    record_count = 0
    root_tag: str | None = None

    with archive.open(member) as stream:
        for event, element in ET.iterparse(stream, events=("start", "end")):
            if root_tag is None and event == "start":
                root_tag = element.tag
            if event != "end" or element.tag != "Law":
                continue
            fields = {child.tag: _normalized_text(child) for child in element}
            observed_fields.update(fields)
            record_count += 1
            for field in expected_schema:
                if not fields.get(field, "").strip():
                    missing_fields[field] += 1
            canonical = json.dumps(
                fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            record_hashes[_sha256_text(canonical)] += 1
            content_hashes[_sha256_text(fields.get("法規內容", ""))] += 1
            identity = "\x1f".join([agency, *(fields.get(field, "") for field in IDENTITY_FIELDS)])
            identity_hashes[_sha256_text(identity)] += 1
            combined_text = "\n".join(fields.get(field, "") for field in TEXT_FIELDS)
            text_lengths.append(len(combined_text))
            records_with_markup += bool(MARKUP.search(combined_text))
            records_with_control_characters += bool(CONTROL_CHARACTERS.search(combined_text))
            for field in DATE_FIELDS:
                raw_date = fields.get(field, "").strip()
                if not raw_date:
                    continue
                date_stats[field]["present"] += 1
                parsed = _parse_tw_date(raw_date)
                if parsed is None:
                    date_stats[field]["failed"] += 1
                else:
                    date_stats[field]["parsed"] += 1
                    date_stats[field]["dates"].append(parsed)
            element.clear()

    issues = []
    if root_tag != "LAWS":
        issues.append("unexpected_xml_root")
    if record_count == 0:
        issues.append("empty_xml")
    if observed_fields != set(expected_schema):
        issues.append("xml_schema_mismatch")
    return (
        {
            "xml_root": root_tag,
            "record_count": record_count,
            "observed_field_count": len(observed_fields),
            "observed_schema_sha256": _hash_sequence(sorted(observed_fields)),
            "missing_field_counts": dict(sorted(missing_fields.items())),
            "date_quality": _date_summary(date_stats),
            "text_length": _length_summary(text_lengths),
            "records_with_markup": records_with_markup,
            "records_with_control_characters": records_with_control_characters,
            "duplicate_groups": {
                "exact_record": _duplicate_group_count(record_hashes),
                "content": _duplicate_group_count(content_hashes),
                "identity": _duplicate_group_count(identity_hashes),
            },
            "duplicate_extra_rows": {
                "exact_record": _duplicate_extra_rows(record_hashes),
                "content": _duplicate_extra_rows(content_hashes),
                "identity": _duplicate_extra_rows(identity_hashes),
            },
            "issues": issues,
        },
        record_hashes,
        content_hashes,
    )


def _read_csv(archive: ZipFile, member: str) -> list[list[str]]:
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        return [[cell.strip() for cell in row] for row in csv.reader(text)]


def _schema_fields(rows: list[list[str]]) -> list[str]:
    values = [row[0] for row in rows if row and row[0]]
    if values and values[0].casefold() in {"field", "name", "欄位", "欄位名稱"}:
        values = values[1:]
    return values


def _valid_manifest(rows: list[list[str]]) -> bool:
    flattened = [cell.casefold() for row in rows for cell in row if cell]
    return bool(flattened) and any(value.endswith(".xml") for value in flattened)


def _normalized_text(element: ET.Element) -> str:
    return "".join(element.itertext()).replace("\r\n", "\n").replace("\r", "\n").strip()


def _parse_tw_date(value: str) -> date | None:
    match = DATE_PARTS.search(value)
    if match:
        year, month, day = map(int, match.groups())
    else:
        compact = COMPACT_DATE.search(value)
        if not compact:
            return None
        digits = compact.group(1)
        year_length = len(digits) - 4
        year, month, day = int(digits[:year_length]), int(digits[year_length:-2]), int(digits[-2:])
    if year <= 300:
        year += 1911
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _date_summary(stats: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    result = {}
    for field, values in stats.items():
        dates = values.pop("dates")
        result[field] = {
            **values,
            "min_date": min(dates).isoformat() if dates else None,
            "max_date": max(dates).isoformat() if dates else None,
        }
    return result


def _length_summary(values: list[int]) -> dict[str, int | float | None]:
    if not values:
        return {"min": None, "median": None, "mean": None, "max": None}
    return {
        "min": min(values),
        "median": statistics.median(values),
        "mean": round(statistics.fmean(values), 2),
        "max": max(values),
    }


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\x00" not in name


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_sequence(values: list[str]) -> str:
    return _sha256_text(json.dumps(values, ensure_ascii=False, separators=(",", ":")))


def _duplicate_group_count(counter: Counter[str]) -> int:
    return sum(count > 1 for count in counter.values())


def _duplicate_extra_rows(counter: Counter[str]) -> int:
    return sum(count - 1 for count in counter.values() if count > 1)


def _cross_source_group_count(sources: dict[str, set[str]]) -> int:
    return sum(len(source_ids) > 1 for source_ids in sources.values())


def _cross_source_extra_rows(
    counter: Counter[str], sources: dict[str, set[str]]
) -> int:
    return sum(
        count - 1
        for digest, count in counter.items()
        if count > 1 and len(sources.get(digest, set())) > 1
    )


def _failed_observation(
    base: dict[str, object], *issues: str, **details: object
) -> dict[str, object]:
    return {
        **base,
        "structural_passed": False,
        "record_count": 0,
        "issues": sorted(set(issues)),
        "error_code": details.pop("error_code", None),
        **details,
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit approved FSC archives without retaining raw text"
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_archives(load_snapshot(args.snapshot), args.archive_dir)
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "overall_passed": report["overall_passed"],
                "archive_count": report["archive_count"],
                "record_count": report["record_count"],
                "raw_content_stored": False,
                "manual_labels_used": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["overall_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
