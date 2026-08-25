from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

LABEL_FIELDS = ("overall", "entity_sentiment", "opinion_sentiment")
TRACEABILITY_FIELDS = ("source_url", "published_at")
VALID_LABELS = {"正面", "中立", "負面", "positive", "neutral", "negative"}
FINANCIAL_TERMS = (
    "營收",
    "獲利",
    "虧損",
    "股利",
    "庫藏股",
    "增資",
    "減資",
    "合併",
    "收購",
    "財報",
    "重大訊息",
    "董事會",
    "股票",
    "公司",
)
OBVIOUS_NON_FINANCIAL_TERMS = (
    "星座",
    "生肖",
    "愛情運",
    "戀愛運",
    "表情包",
    "遊戲伺服器",
)
TRADITIONAL_MARKERS = set("臺灣體股與為後發裡這個資訊營運獲利虧損處分會議")
SIMPLIFIED_MARKERS = set("台湾体与为后发里这个资讯营运获利亏损处分会议")


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", text).strip()


def read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.casefold()
    if suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            return payload["rows"]
        if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
            return payload["samples"]
        raise ValueError(f"unsupported JSON structure: {path}")
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".parquet":
        try:
            import pyarrow.parquet as parquet
        except ImportError as error:
            raise RuntimeError(
                "parquet audit requires optional dependency: pip install -e '.[audit]'"
            ) from error
        return parquet.read_table(path).to_pylist()
    raise ValueError(f"unsupported file type: {path.suffix}")


def audit_dataset(
    split_rows: dict[str, list[dict[str, Any]]],
    *,
    dataset_id: str,
    dataset_revision: str,
    declared_license: str,
    fuzzy_threshold: float = 0.92,
) -> dict[str, object]:
    if not 0.0 <= fuzzy_threshold <= 1.0:
        raise ValueError("fuzzy_threshold must be between 0 and 1")

    records = [
        _record(split, index, row)
        for split, rows in sorted(split_rows.items())
        for index, row in enumerate(rows)
    ]
    normalized_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["normalized_text"]:
            normalized_groups[record["normalized_text"]].append(record)
    duplicate_groups = [group for group in normalized_groups.values() if len(group) > 1]
    cross_split_groups = [
        group if len({row["split"] for row in group}) > 1 else [] for group in duplicate_groups
    ]
    cross_split_groups = [group for group in cross_split_groups if group]
    fuzzy_pairs = _fuzzy_cross_split_pairs(records, fuzzy_threshold)

    fields = sorted({key for row in records for key in row["raw"].keys()})
    label_distributions = {
        field: dict(
            sorted(Counter(str(row["raw"].get(field) or "<missing>") for row in records).items())
        )
        for field in LABEL_FIELDS
        if field in fields
    }
    unknown_labels = sorted(
        {
            str(row["effective_label"])
            for row in records
            if row["effective_label"] and str(row["effective_label"]).casefold() not in VALID_LABELS
        }
    )
    label_conflicts = sum(
        len({row["effective_label"] for row in group if row["effective_label"]}) > 1
        for group in duplicate_groups
    )
    text_lengths = [len(row["normalized_text"]) for row in records if row["normalized_text"]]
    missing_traceability = {
        field: sum(not row["raw"].get(field) for row in records) for field in TRACEABILITY_FIELDS
    }
    non_financial_rows = sum(row["non_financial_marker"] for row in records)
    reasons = []
    if any(missing_traceability.values()):
        reasons.append("missing source_url and/or published_at lineage")
    if cross_split_groups:
        reasons.append("exact text leakage exists across splits")
    if fuzzy_pairs:
        reasons.append("heuristic near-duplicate leakage candidates exist across splits")
    if label_conflicts:
        reasons.append("duplicate texts contain conflicting effective labels")
    if unknown_labels:
        reasons.append("unknown labels require mapping review")
    if records and non_financial_rows / len(records) > 0.05:
        reasons.append("obvious non-financial marker rate exceeds 5%")

    return {
        "audit_schema_version": "taiwan-dataset-audit-v1",
        "dataset_id": dataset_id,
        "dataset_revision": dataset_revision,
        "declared_license": declared_license,
        "row_count": len(records),
        "split_counts": {split: len(rows) for split, rows in sorted(split_rows.items())},
        "fields": fields,
        "task_distribution": _distribution(records, "task"),
        "source_distribution": _distribution(records, "source"),
        "label_distributions": label_distributions,
        "unknown_effective_labels": unknown_labels,
        "missing_text_rows": sum(not row["normalized_text"] for row in records),
        "missing_entity_rows": sum(not row["raw"].get("entity") for row in records),
        "missing_traceability": missing_traceability,
        "text_length": _length_summary(text_lengths),
        "language_markers": {
            "traditional_marker_rows": sum(row["traditional_marker"] for row in records),
            "simplified_marker_rows": sum(row["simplified_marker"] for row in records),
            "mixed_marker_rows": sum(
                row["traditional_marker"] and row["simplified_marker"] for row in records
            ),
            "note": "marker heuristic only; not a language classifier",
        },
        "domain_markers": {
            "financial_marker_rows": sum(row["financial_marker"] for row in records),
            "obvious_non_financial_marker_rows": non_financial_rows,
            "note": "keyword screen only; manual source/domain review remains required",
        },
        "duplicates": {
            "exact_group_count": len(duplicate_groups),
            "exact_cross_split_group_count": len(cross_split_groups),
            "conflicting_label_group_count": label_conflicts,
            "cross_split_group_hashes": [
                _group_summary(group) for group in cross_split_groups[:100]
            ],
            "fuzzy_threshold": fuzzy_threshold,
            "fuzzy_cross_split_candidate_count": len(fuzzy_pairs),
            "fuzzy_cross_split_candidates": fuzzy_pairs[:100],
            "fuzzy_method": "character 5-gram candidate retrieval + SequenceMatcher",
        },
        "automated_screen": {
            "passed": not reasons,
            "reasons": reasons,
            "decision_note": (
                "automated screen is necessary but not sufficient for training approval"
            ),
        },
        "raw_text_in_report": False,
    }


def _record(split: str, index: int, row: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(row.get("text"))
    task = normalize_text(row.get("task"))
    if task == "entity":
        effective_label = row.get("entity_sentiment")
    elif task == "opinion":
        effective_label = row.get("opinion_sentiment")
    else:
        effective_label = row.get("overall")
    return {
        "split": split,
        "index": index,
        "raw": row,
        "normalized_text": text[:4000],
        "effective_label": effective_label,
        "financial_marker": any(term in text for term in FINANCIAL_TERMS),
        "non_financial_marker": any(term in text for term in OBVIOUS_NON_FINANCIAL_TERMS),
        "traditional_marker": any(marker in text for marker in TRADITIONAL_MARKERS),
        "simplified_marker": any(marker in text for marker in SIMPLIFIED_MARKERS),
    }


def _distribution(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(
        sorted(Counter(str(row["raw"].get(field) or "<missing>") for row in records).items())
    )


def _length_summary(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"min": 0, "median": 0, "max": 0, "mean": 0.0}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "min": ordered[0],
        "median": median,
        "max": ordered[-1],
        "mean": round(sum(ordered) / len(ordered), 2),
    }


def _group_summary(group: list[dict[str, Any]]) -> dict[str, object]:
    digest = hashlib.sha256(group[0]["normalized_text"].encode()).hexdigest()
    return {
        "text_sha256": digest,
        "splits": sorted({row["split"] for row in group}),
        "row_count": len(group),
    }


def _fuzzy_cross_split_pairs(
    records: list[dict[str, Any]], threshold: float
) -> list[dict[str, object]]:
    eligible = [row for row in records if len(row["normalized_text"]) >= 20]
    shingle_index: dict[str, list[int]] = defaultdict(list)
    shingles_by_index: list[set[str]] = []
    for index, row in enumerate(eligible):
        shingles = _shingles(row["normalized_text"], 5)
        shingles_by_index.append(shingles)
        for shingle in shingles:
            if len(shingle_index[shingle]) < 100:
                shingle_index[shingle].append(index)

    candidates: set[tuple[int, int]] = set()
    for indexes in shingle_index.values():
        for position, left in enumerate(indexes):
            for right in indexes[position + 1 :]:
                if eligible[left]["split"] != eligible[right]["split"]:
                    candidates.add((left, right))

    output = []
    for left_index, right_index in sorted(candidates):
        left = eligible[left_index]
        right = eligible[right_index]
        left_shingles = shingles_by_index[left_index]
        right_shingles = shingles_by_index[right_index]
        union = left_shingles | right_shingles
        jaccard = len(left_shingles & right_shingles) / len(union) if union else 0.0
        if jaccard < 0.70:
            continue
        similarity = SequenceMatcher(
            None, left["normalized_text"], right["normalized_text"], autojunk=False
        ).ratio()
        if similarity < threshold or left["normalized_text"] == right["normalized_text"]:
            continue
        output.append(
            {
                "left_split": left["split"],
                "left_index": left["index"],
                "right_split": right["split"],
                "right_index": right["index"],
                "similarity": round(similarity, 6),
                "left_sha256": hashlib.sha256(left["normalized_text"].encode()).hexdigest(),
                "right_sha256": hashlib.sha256(right["normalized_text"].encode()).hexdigest(),
            }
        )
    return output


def _shingles(text: str, size: int) -> set[str]:
    compact = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", text)[:2000]
    if len(compact) <= size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(len(compact) - size + 1)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Taiwan/Chinese sentiment datasets without emitting raw text"
    )
    parser.add_argument(
        "--split",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Repeat for train, validation and test files",
    )
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--declared-license", required=True)
    parser.add_argument("--fuzzy-threshold", type=float, default=0.92)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    split_paths = {}
    for value in args.split:
        if "=" not in value:
            raise ValueError("--split must use NAME=PATH")
        name, raw_path = value.split("=", 1)
        if not name or not raw_path:
            raise ValueError("--split must use non-empty NAME=PATH")
        if name in split_paths:
            raise ValueError(f"duplicate split name: {name}")
        split_paths[name] = Path(raw_path)
    report = audit_dataset(
        {name: read_rows(path) for name, path in split_paths.items()},
        dataset_id=args.dataset_id,
        dataset_revision=args.dataset_revision,
        declared_license=args.declared_license,
        fuzzy_threshold=args.fuzzy_threshold,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["automated_screen"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
