from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

AUDIT_VERSION = "finmind-news-metadata-audit-v1"
DEFAULT_CONFIG = Path("research/configs/finmind_news_audit.v1.json")
DEFAULT_OUTPUT = Path("artifacts/finmind-news-metadata-audit.json")


class FinMindNewsAuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    audit_version: Literal["finmind-news-metadata-audit-v1"] = AUDIT_VERSION
    endpoint: HttpUrl
    dataset_id: Literal["TaiwanStockNews"]
    ticker: str = Field(pattern=r"^[0-9A-Z]{2,12}$")
    sample_dates: list[date] = Field(min_length=1, max_length=10)
    required_fields: list[str] = Field(min_length=1)
    max_response_bytes: int = Field(gt=0, le=5_000_000)
    timestamp_semantics_documented: Literal[False] = False
    timezone_documented: Literal[False] = False
    retention_policy: Literal["aggregate_hashes_only"]

    @field_validator("sample_dates", "required_fields")
    @classmethod
    def unique_values(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("audit values must be unique")
        return value


def load_config(path: Path) -> FinMindNewsAuditConfig:
    return FinMindNewsAuditConfig.model_validate_json(path.read_text(encoding="utf-8"))


def audit_finmind_news(
    config: FinMindNewsAuditConfig,
    *,
    client: httpx.Client | None = None,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = retrieved_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "financial-ai-assistant/0.1 metadata-audit"},
    )
    observations = []
    try:
        for sample_date in config.sample_dates:
            observations.append(_audit_day(config, sample_date, active_client))
    finally:
        if owns_client:
            active_client.close()

    total_records = sum(int(row["record_count"]) for row in observations)
    timezone_aware = sum(int(row["timezone_aware_timestamp_count"]) for row in observations)
    exact_duplicates = sum(int(row["exact_link_duplicate_count"]) for row in observations)
    all_passed = all(bool(row["schema_passed"]) for row in observations)
    return {
        "audit_version": config.audit_version,
        "retrieved_at": observed_at.astimezone(UTC).isoformat(),
        "dataset_id": config.dataset_id,
        "ticker": config.ticker,
        "requested_dates": [item.isoformat() for item in config.sample_dates],
        "request_count": len(observations),
        "successful_schema_count": sum(bool(row["schema_passed"]) for row in observations),
        "record_count": total_records,
        "timezone_aware_timestamp_count": timezone_aware,
        "exact_link_duplicate_count": exact_duplicates,
        "observations": observations,
        "schema_gate_passed": all_passed,
        "timestamp_semantics_documented": False,
        "timezone_documented": False,
        "direct_reaction_event_decision": "HOLD",
        "decision_reasons": [
            "timestamp_semantics_not_documented",
            "timezone_not_documented",
            "underlying_publisher_rights_not_inherited",
            "cross_publisher_duplicate_policy_required",
        ],
        "raw_content_stored": False,
        "titles_stored": False,
        "descriptions_stored": False,
        "links_stored": False,
        "manual_labels_used": False,
        "sentiment_ground_truth": False,
    }


def _audit_day(
    config: FinMindNewsAuditConfig,
    sample_date: date,
    client: httpx.Client,
) -> dict[str, object]:
    response = client.get(
        str(config.endpoint),
        params={
            "dataset": config.dataset_id,
            "data_id": config.ticker,
            "start_date": sample_date.isoformat(),
        },
    )
    response.raise_for_status()
    if len(response.content) > config.max_response_bytes:
        raise ValueError("FinMind news response exceeded audit byte limit")
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("FinMind news response did not contain a data list")
    rows = payload["data"]
    if any(not isinstance(row, dict) for row in rows):
        raise TypeError("FinMind news rows must be objects")
    observed_fields = sorted({str(key) for row in rows for key in row})
    missing_fields = sorted(set(config.required_fields) - set(observed_fields))
    timestamp_formats = Counter()
    timezone_aware_count = 0
    link_hashes = []
    for row in rows:
        parsed = datetime.fromisoformat(str(row["date"]))
        timestamp_kind = (
            "datetime" if parsed.time().isoformat() != "00:00:00" else "midnight"
        )
        timestamp_formats[timestamp_kind] += 1
        timezone_aware_count += parsed.tzinfo is not None
        link_hashes.append(hashlib.sha256(str(row["link"]).encode()).hexdigest())
    link_counts = Counter(link_hashes)
    canonical_schema = json.dumps(observed_fields, separators=(",", ":")).encode()
    return {
        "requested_date": sample_date.isoformat(),
        "http_status": response.status_code,
        "record_count": len(rows),
        "observed_fields": observed_fields,
        "missing_fields": missing_fields,
        "schema_sha256": hashlib.sha256(canonical_schema).hexdigest(),
        "timestamp_format_counts": dict(sorted(timestamp_formats.items())),
        "timezone_aware_timestamp_count": timezone_aware_count,
        "distinct_link_hash_count": len(link_counts),
        "exact_link_duplicate_count": sum(count - 1 for count in link_counts.values()),
        "schema_passed": bool(rows) and not missing_fields,
        "raw_content_stored": False,
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a raw-free FinMind news metadata audit")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_finmind_news(load_config(args.config))
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "record_count": report["record_count"],
                "schema_gate_passed": report["schema_gate_passed"],
                "direct_reaction_event_decision": "HOLD",
                "raw_content_stored": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["schema_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
