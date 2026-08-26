from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research.evaluation.fsc_archive_audit import (
    ArchiveSnapshot,
    audit_archives,
    load_snapshot,
)

CORPUS_VERSION = "fsc-domain-corpus-v1"
REPORT_VERSION = "fsc-domain-corpus-build-report-v1"
DEFAULT_CONFIG = Path("research/configs/fsc_domain_corpus.v1.json")
DEFAULT_SNAPSHOT = Path("research/configs/fsc_official_archive_snapshot.v1.json")
DEFAULT_ARCHIVE_DIR = Path(".tools/datasets/fsc-official")
DEFAULT_OUTPUT_DIR = Path(".tools/corpora/fsc-domain-corpus-v1")
DEFAULT_REPORT = Path("artifacts/fsc-domain-corpus-build-report.json")
SAFE_RAW_OUTPUT_ROOTS = (Path(".tools"), Path("data/raw"))
DATE_PARTS = re.compile(r"(?<!\d)(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})(?!\d)")
COMPACT_DATE = re.compile(r"(?<!\d)(\d{7,8})(?!\d)")
WHITESPACE = re.compile(r"[\t\f\v ]+")
BLANK_LINES = re.compile(r"\n{3,}")


class CorpusConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    corpus_version: Literal["fsc-domain-corpus-v1"] = CORPUS_VERSION
    normalization_version: Literal["nfkc-whitespace-v1"] = "nfkc-whitespace-v1"
    train_end: date
    validation_end: date
    family_field_priority: list[str] = Field(min_length=1)
    text_field: str = Field(min_length=1)
    publication_date_field: str = Field(min_length=1)
    revision_date_field: str = Field(min_length=1)
    allowed_use: str = Field(min_length=1)
    forbidden_uses: list[str] = Field(min_length=1)

    @field_validator("family_field_priority", "forbidden_uses")
    @classmethod
    def require_unique_values(cls, value: list[str]) -> list[str]:
        if any(not item for item in value) or len(value) != len(set(value)):
            raise ValueError("list values must be non-empty and unique")
        return value

    @model_validator(mode="after")
    def validate_boundaries(self) -> CorpusConfig:
        if self.train_end >= self.validation_end:
            raise ValueError("train_end must be earlier than validation_end")
        if self.text_field in self.family_field_priority:
            raise ValueError("text_field cannot be a family identity field")
        return self


def load_config(path: Path) -> CorpusConfig:
    return CorpusConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_corpus(
    config: CorpusConfig,
    snapshot: ArchiveSnapshot,
    archive_dir: Path,
    output_dir: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = generated_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")

    archive_report = audit_archives(snapshot, archive_dir, generated_at=observed_at)
    if not archive_report["overall_passed"]:
        raise ValueError("FSC archive audit must pass before corpus construction")

    exclusions: Counter[str] = Counter()
    candidates: list[dict[str, str]] = []
    for definition in snapshot.archives:
        path = archive_dir / definition.local_filename
        with ZipFile(path) as archive:
            xml_member = next(
                info.filename
                for info in archive.infolist()
                if not info.is_dir() and info.filename.casefold().endswith(".xml")
            )
            with archive.open(xml_member) as stream:
                for _, element in ET.iterparse(stream, events=("end",)):
                    if element.tag != "Law":
                        continue
                    fields = {
                        child.tag: normalize_text("".join(child.itertext()))
                        for child in element
                    }
                    content = fields.get(config.text_field, "")
                    if not content:
                        exclusions["empty_content"] += 1
                        element.clear()
                        continue
                    publication_date = parse_tw_date(
                        fields.get(config.publication_date_field, "")
                    )
                    if publication_date is None:
                        exclusions["invalid_publication_date"] += 1
                        element.clear()
                        continue
                    revision_date = parse_tw_date(fields.get(config.revision_date_field, ""))
                    content_sha256 = sha256_text(content)
                    family_basis = _family_basis(
                        fields, config.family_field_priority, content_sha256
                    )
                    family_sha256 = sha256_text(f"{definition.agency}\x1f{family_basis}")
                    candidates.append(
                        {
                            "source_id": definition.source_id,
                            "agency": definition.agency,
                            "publication_date": publication_date.isoformat(),
                            "revision_date": revision_date.isoformat() if revision_date else "",
                            "family_sha256": family_sha256,
                            "content_sha256": content_sha256,
                            "text": content,
                        }
                    )
                    element.clear()

    candidates.sort(
        key=lambda row: (
            row["publication_date"],
            row["agency"],
            row["family_sha256"],
            row["content_sha256"],
        )
    )
    retained_by_content: dict[str, dict[str, str]] = {}
    for row in candidates:
        if row["content_sha256"] in retained_by_content:
            exclusions["duplicate_content"] += 1
            continue
        retained_by_content[row["content_sha256"]] = row
    retained = list(retained_by_content.values())

    family_anchor = _family_anchor_dates(retained)
    split_rows: dict[str, list[dict[str, str]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    for row in retained:
        split = _split_for_date(family_anchor[row["family_sha256"]], config)
        public_row = {
            "record_id": sha256_text(
                "\x1f".join(
                    [row["source_id"], row["publication_date"], row["content_sha256"]]
                )
            ),
            **row,
        }
        split_rows[split].append(public_row)

    for rows in split_rows.values():
        rows.sort(key=lambda row: (row["publication_date"], row["record_id"]))
    _validate_split_isolation(split_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    split_files = {}
    for split, rows in split_rows.items():
        payload = _jsonl_bytes(rows)
        target = output_dir / f"{split}.jsonl"
        _write_immutable(target, payload)
        split_files[split] = {
            "record_count": len(rows),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "min_publication_date": rows[0]["publication_date"] if rows else None,
            "max_publication_date": rows[-1]["publication_date"] if rows else None,
            "family_count": len({row["family_sha256"] for row in rows}),
        }

    semantic_rows = [row for split in ("train", "validation", "test") for row in split_rows[split]]
    semantic_payload = _jsonl_bytes(semantic_rows)
    report = {
        "report_version": REPORT_VERSION,
        "corpus_version": config.corpus_version,
        "normalization_version": config.normalization_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "source_snapshot_version": snapshot.snapshot_version,
        "source_archive_sha256": {
            item.source_id: item.expected_sha256 for item in snapshot.archives
        },
        "allowed_use": config.allowed_use,
        "forbidden_uses": config.forbidden_uses,
        "split_policy": {
            "method": "family_max_publication_date",
            "train_end": config.train_end.isoformat(),
            "validation_end": config.validation_end.isoformat(),
            "test_is_sealed": True,
        },
        "input_record_count": int(archive_report["record_count"]),
        "retained_record_count": len(semantic_rows),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "split_files": split_files,
        "corpus_sha256": hashlib.sha256(semantic_payload).hexdigest(),
        "raw_text_output_directory": str(output_dir),
        "raw_content_committed": False,
        "manual_labels_used": False,
        "manual_review_used": False,
        "sentiment_ground_truth": False,
    }
    immutable_manifest = {key: value for key, value in report.items() if key != "generated_at"}
    _write_immutable(
        output_dir / "manifest.json",
        (
            json.dumps(immutable_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode(),
    )
    return report


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE.sub(" ", line).strip() for line in normalized.splitlines()]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def parse_tw_date(value: str) -> date | None:
    match = DATE_PARTS.search(value)
    if match:
        year, month, day = map(int, match.groups())
    else:
        compact = COMPACT_DATE.search(value)
        if not compact:
            return None
        digits = compact.group(1)
        year_length = len(digits) - 4
        year = int(digits[:year_length])
        month = int(digits[year_length:-2])
        day = int(digits[-2:])
    if year <= 300:
        year += 1911
    try:
        return date(year, month, day)
    except ValueError:
        return None


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _family_basis(fields: dict[str, str], priority: list[str], content_hash: str) -> str:
    for field in priority:
        value = fields.get(field, "")
        if value:
            return f"{field}\x1f{value}"
    return f"content_sha256\x1f{content_hash}"


def _family_anchor_dates(rows: list[dict[str, str]]) -> dict[str, date]:
    anchors: dict[str, date] = {}
    for row in rows:
        family = row["family_sha256"]
        publication_date = date.fromisoformat(row["publication_date"])
        anchors[family] = max(anchors.get(family, publication_date), publication_date)
    return anchors


def _split_for_date(value: date, config: CorpusConfig) -> str:
    if value <= config.train_end:
        return "train"
    if value <= config.validation_end:
        return "validation"
    return "test"


def _validate_split_isolation(split_rows: dict[str, list[dict[str, str]]]) -> None:
    content_splits: dict[str, set[str]] = {}
    family_splits: dict[str, set[str]] = {}
    for split, rows in split_rows.items():
        for row in rows:
            content_splits.setdefault(row["content_sha256"], set()).add(split)
            family_splits.setdefault(row["family_sha256"], set()).add(split)
    if any(len(splits) > 1 for splits in content_splits.values()):
        raise ValueError("content hash leakage detected across splits")
    if any(len(splits) > 1 for splits in family_splits.values()):
        raise ValueError("document family leakage detected across splits")


def _jsonl_bytes(rows: list[dict[str, str]]) -> bytes:
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite a different existing file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _require_safe_raw_output(path: Path) -> None:
    resolved = path.resolve()
    safe_roots = [(Path.cwd() / root).resolve() for root in SAFE_RAW_OUTPUT_ROOTS]
    if not any(resolved.is_relative_to(root) for root in safe_roots):
        raise ValueError("raw corpus output must be inside .tools/ or data/raw/")


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a filtered, family-isolated FSC domain corpus snapshot"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _require_safe_raw_output(args.output_dir)
    report = build_corpus(
        load_config(args.config),
        load_snapshot(args.snapshot),
        args.archive_dir,
        args.output_dir,
    )
    write_report(args.report, report)
    print(
        json.dumps(
            {
                "report": str(args.report),
                "corpus_sha256": report["corpus_sha256"],
                "retained_record_count": report["retained_record_count"],
                "split_counts": {
                    split: details["record_count"]
                    for split, details in report["split_files"].items()
                },
                "manual_labels_used": False,
                "sentiment_ground_truth": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
