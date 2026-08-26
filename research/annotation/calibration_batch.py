from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipelines.news.normalization import normalize_title

CALIBRATION_SCHEMA_VERSION = "taiwan-calibration-candidate-v1"
PRIVATE_OUTPUT_ROOTS = (Path("artifacts"), Path(".tools"), Path("data/raw"))


@dataclass(frozen=True)
class AnnouncementCandidate:
    source: str
    source_type: str
    source_url: str
    source_record_id: str | None
    published_at: datetime
    ticker: str
    entity_name: str
    title: str
    context: str | None
    content_hash: str
    title_fingerprint: str


def build_calibration_batch(
    candidates: Iterable[AnnouncementCandidate],
    *,
    limit: int,
    excluded_texts: Iterable[str] = (),
) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be positive")

    excluded = {normalize_title(text) for text in excluded_texts}
    deduplicated: list[AnnouncementCandidate] = []
    seen_content: set[str] = set()
    seen_titles: set[str] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (item.published_at, item.ticker, item.content_hash),
    ):
        normalized_title = normalize_title(candidate.title)
        if (
            candidate.source != "twse_material"
            or candidate.source_type != "official_announcement"
            or normalized_title in excluded
            or candidate.content_hash in seen_content
            or candidate.title_fingerprint in seen_titles
        ):
            continue
        seen_content.add(candidate.content_hash)
        seen_titles.add(candidate.title_fingerprint)
        deduplicated.append(candidate)

    by_ticker: dict[str, deque[AnnouncementCandidate]] = defaultdict(deque)
    for candidate in deduplicated:
        by_ticker[candidate.ticker].append(candidate)

    selected: list[AnnouncementCandidate] = []
    tickers = sorted(by_ticker)
    while tickers and len(selected) < limit:
        remaining = []
        for ticker in tickers:
            selected.append(by_ticker[ticker].popleft())
            if by_ticker[ticker]:
                remaining.append(ticker)
            if len(selected) == limit:
                break
        tickers = remaining

    return [_to_template(candidate) for candidate in selected]


def ensure_private_output_path(path: Path, *, cwd: Path | None = None) -> Path:
    workspace = (cwd or Path.cwd()).resolve()
    resolved = path.resolve() if path.is_absolute() else (workspace / path).resolve()
    allowed_roots = [(workspace / root).resolve() for root in PRIVATE_OUTPUT_ROOTS]
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots):
        raise ValueError("calibration batches must stay under artifacts/, .tools/, or data/raw/")
    return resolved


def write_calibration_batch(path: Path, rows: list[dict[str, object]]) -> None:
    output = ensure_private_output_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _to_template(candidate: AnnouncementCandidate) -> dict[str, object]:
    retained_text = "\n".join(filter(None, (candidate.title, candidate.context)))
    source_identity = "|".join(
        (
            candidate.source,
            candidate.source_record_id or candidate.content_hash,
            candidate.ticker,
        )
    )
    return {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "candidate_id": hashlib.sha256(source_identity.encode()).hexdigest(),
        "source_name": candidate.source,
        "source_type": candidate.source_type,
        "source_url": candidate.source_url,
        "source_record_id": candidate.source_record_id,
        "published_at": candidate.published_at.isoformat(),
        "ticker": candidate.ticker,
        "entity_name": candidate.entity_name,
        "title": candidate.title,
        "context": candidate.context,
        "text_sha256": hashlib.sha256(_normalize_retained_text(retained_text).encode()).hexdigest(),
        "split_group_id": candidate.source_record_id or candidate.content_hash,
        "event_type": None,
        "impact_label": None,
        "confidence": None,
        "ambiguous_reason": None,
        "reviewer_1": None,
        "reviewer_2": None,
        "review_status": "DRAFT",
        "adjudicated_label": None,
        "include_for_training": False,
        "exclusion_reason": None,
    }


def _normalize_retained_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()
