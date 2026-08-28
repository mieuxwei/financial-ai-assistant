from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

PROBE_VERSION = "twmd-major-event-probe-v1"
DEFAULT_CONFIG = Path("research/configs/twmd_major_event_probe.v1.json")
DEFAULT_OUTPUT = Path("artifacts/twmd-major-event-probe.json")
DEFAULT_CACHE = Path(".tools/datasets/twmd-major-event-probe")
REQUIRED_FIELDS = {
    "ticker",
    "market",
    "event_date",
    "event_time",
    "subject",
    "event_class",
    "confidence",
    "rule_version",
}


class ProbePeriod(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(pattern=r"^[a-z0-9_]+$")
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> ProbePeriod:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if self.end_date >= date(2025, 1, 1):
            raise ValueError("probe periods must remain before the 2025 sealed-test boundary")
        return self


class TwmdProbeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    probe_version: Literal["twmd-major-event-probe-v1"] = PROBE_VERSION
    endpoint: HttpUrl
    symbol: str = Field(pattern=r"^[0-9A-Z]{2,12}$")
    periods: list[ProbePeriod] = Field(min_length=1, max_length=12)
    limit: int = Field(ge=1, le=10_000)
    timeout_seconds: float = Field(gt=0, le=120)
    max_response_bytes: int = Field(gt=0, le=50_000_000)
    api_key_environment_variable: Literal["TWMD_API_KEY"]
    raw_retention: Literal["ignored_local_cache_only"]

    @field_validator("periods")
    @classmethod
    def validate_unique_period_labels(cls, value: list[ProbePeriod]) -> list[ProbePeriod]:
        labels = [period.label for period in value]
        if len(labels) != len(set(labels)):
            raise ValueError("period labels must be unique")
        return value


def load_config(path: Path) -> TwmdProbeConfig:
    return TwmdProbeConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_api_key(variable: str, env_file: Path = Path(".env")) -> str:
    value = os.environ.get(variable, "").strip()
    if value:
        return value
    if env_file.exists():
        prefix = f"{variable}="
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(prefix):
                value = line[len(prefix) :].strip().strip("'\"")
                if value:
                    return value
    raise RuntimeError(f"{variable} is missing; store it in the environment or ignored .env")


def fetch_period(
    client: httpx.Client,
    config: TwmdProbeConfig,
    period: ProbePeriod,
    cache_dir: Path,
) -> dict[str, object]:
    path = cache_dir / config.symbol / f"{period.label}.json"
    cache_hit = path.exists()
    if cache_hit:
        payload_bytes = path.read_bytes()
        status_code = 200
    else:
        response = client.get(
            str(config.endpoint),
            params={
                "symbol": config.symbol,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "limit": config.limit,
            },
        )
        status_code = response.status_code
        if response.is_error:
            return {
                "label": period.label,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "status_code": status_code,
                "cache_hit": False,
                "payload_sha256": None,
                "declared_data_count": None,
                "request_context": None,
                "rows": [],
                "known_gaps": [],
                "warnings": [],
                "error_code": f"HTTP_{status_code}",
            }
        payload_bytes = response.content
        if len(payload_bytes) > config.max_response_bytes:
            raise ValueError("TWMD response exceeded max_response_bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload_bytes)
    if len(payload_bytes) > config.max_response_bytes:
        raise ValueError("cached TWMD response exceeded max_response_bytes")
    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("TWMD response did not contain a data list")
    if any(not isinstance(row, dict) for row in payload["data"]):
        raise TypeError("TWMD rows must be objects")
    return {
        "label": period.label,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
        "status_code": status_code,
        "cache_hit": cache_hit,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "declared_data_count": payload.get("data_count"),
        "request_context": payload.get("request_context"),
        "rows": payload["data"],
        "known_gaps": payload.get("known_gaps", []),
        "warnings": payload.get("warnings", []),
        "error_code": None,
    }


def summarize_result(result: dict[str, object], *, symbol: str, limit: int) -> dict[str, object]:
    rows = result["rows"]
    assert isinstance(rows, list)
    schemas = Counter(tuple(sorted(row)) for row in rows)
    dates: list[date] = []
    valid_time_count = 0
    nonempty_subject_count = 0
    ticker_match_count = 0
    rule_versions: Counter[str] = Counter()
    event_classes: Counter[str] = Counter()
    identity_hashes: list[str] = []
    for row in rows:
        assert isinstance(row, dict)
        try:
            dates.append(date.fromisoformat(str(row.get("event_date", ""))))
        except ValueError:
            pass
        if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d", str(row.get("event_time", ""))):
            valid_time_count += 1
        subject = str(row.get("subject", "")).strip()
        nonempty_subject_count += bool(subject)
        ticker_match_count += str(row.get("ticker", "")) == symbol
        rule_versions[str(row.get("rule_version", ""))] += 1
        event_classes[str(row.get("event_class", ""))] += 1
        identity = "\x1f".join(
            str(row.get(field, ""))
            for field in ("ticker", "event_date", "event_time", "subject", "rule_version")
        )
        identity_hashes.append(hashlib.sha256(identity.encode()).hexdigest())
    count = len(rows)
    unique_identities = len(set(identity_hashes))
    return {
        "label": result["label"],
        "requested_start_date": result["start_date"],
        "requested_end_date": result["end_date"],
        "status_code": result["status_code"],
        "cache_hit": result["cache_hit"],
        "payload_sha256": result["payload_sha256"],
        "row_count": count,
        "declared_data_count": result["declared_data_count"],
        "limit_reached": count >= limit,
        "min_event_date": min(dates).isoformat() if dates else None,
        "max_event_date": max(dates).isoformat() if dates else None,
        "valid_event_date_rate": len(dates) / count if count else None,
        "valid_event_time_rate": valid_time_count / count if count else None,
        "nonempty_subject_rate": nonempty_subject_count / count if count else None,
        "ticker_match_rate": ticker_match_count / count if count else None,
        "exact_identity_duplicate_count": count - unique_identities,
        "schema_variants": [
            {"fields": list(fields), "count": schema_count}
            for fields, schema_count in sorted(schemas.items())
        ],
        "required_fields_present_in_all_rows": all(REQUIRED_FIELDS <= set(row) for row in rows),
        "rule_version_counts": dict(sorted(rule_versions.items())),
        "event_class_counts": dict(sorted(event_classes.items())),
        "known_gaps": result["known_gaps"],
        "warnings": result["warnings"],
        "error_code": result.get("error_code"),
        "raw_subjects_excluded_from_report": True,
    }


def run_probe(
    config: TwmdProbeConfig,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    output_path: Path = DEFAULT_OUTPUT,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = retrieved_at or datetime.now(UTC)
    api_key = load_api_key(config.api_key_environment_variable)
    headers = {
        "X-API-Key": api_key,
        "User-Agent": "financial-ai-assistant/0.1 twmd-source-audit",
    }
    results: list[dict[str, object]] = []
    with httpx.Client(
        headers=headers,
        timeout=httpx.Timeout(config.timeout_seconds, connect=10.0),
        follow_redirects=True,
    ) as client:
        for period in config.periods:
            fetched = fetch_period(client, config, period, cache_dir)
            results.append(summarize_result(fetched, symbol=config.symbol, limit=config.limit))
    report = {
        "probe_version": config.probe_version,
        "retrieved_at": observed_at.isoformat(),
        "endpoint": str(config.endpoint),
        "symbol": config.symbol,
        "request_count": len(config.periods),
        "api_key_recorded": False,
        "raw_content_committed": False,
        "local_cache_path": str(cache_dir),
        "periods": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe TWMD major-event history safely.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_probe(load_config(args.config), cache_dir=args.cache_dir, output_path=args.output)
    summary = [(period["label"], period["row_count"]) for period in report["periods"]]
    print(f"TWMD probe complete: {summary}")


if __name__ == "__main__":
    main()
