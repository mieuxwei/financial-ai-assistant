from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

AUDIT_VERSION = "twmd-pro-reaudit-v1"
DEFAULT_CONFIG = Path("research/configs/twmd_pro_reaudit.v1.json")
DEFAULT_CACHE = Path(".tools/datasets/twmd-pro-reaudit-v1")
DEFAULT_OUTPUT = Path("artifacts/twmd-pro-reaudit-v1.json")
TIMESTAMP_FIELDS = {
    "event_date",
    "event_time",
    "published_at",
    "announcement_date",
    "freshness",
    "as_of_date",
}
TITLE_FIELDS = {"subject", "title", "headline", "summary"}
FULL_TEXT_FIELDS = {"body", "content", "full_text", "description", "detail"}
IDENTITY_FIELDS = {"ticker", "symbol", "company_code", "company_name", "market"}


class AuditProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(pattern=r"^[a-z0-9_]+$")
    endpoint: HttpUrl
    params: dict[str, str | int | bool]

    @field_validator("params")
    @classmethod
    def enforce_small_probe(cls, value: dict[str, str | int | bool]) -> dict[str, str | int | bool]:
        limit = value.get("limit", 1)
        if not isinstance(limit, int) or not 1 <= limit <= 2:
            raise ValueError("each bounded audit probe must use limit 1 or 2")
        return value


class TwmdProReauditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    audit_version: Literal["twmd-pro-reaudit-v1"] = AUDIT_VERSION
    api_key_environment_variable: Literal["TWMD_API_KEY"]
    timeout_seconds: float = Field(gt=0, le=60)
    max_response_bytes: int = Field(gt=0, le=2_000_000)
    raw_retention: Literal["ignored_local_cache_only"]
    probes: list[AuditProbe] = Field(min_length=1, max_length=10)

    @field_validator("probes")
    @classmethod
    def unique_labels(cls, value: list[AuditProbe]) -> list[AuditProbe]:
        labels = [probe.label for probe in value]
        if len(labels) != len(set(labels)):
            raise ValueError("probe labels must be unique")
        return value


def load_config(path: Path) -> TwmdProReauditConfig:
    return TwmdProReauditConfig.model_validate_json(path.read_text(encoding="utf-8"))


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


def _extract_rows(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    envelope = payload.get("envelope")
    if isinstance(envelope, dict):
        nested_data = envelope.get("data")
        if isinstance(nested_data, list):
            return [row for row in nested_data if isinstance(row, dict)]
        if isinstance(nested_data, dict):
            return [nested_data]
    return []


def _has_nonempty(row: dict[str, object], candidates: set[str]) -> bool:
    return any(field in row and row[field] not in (None, "", [], {}) for field in candidates)


def summarize_payload(
    *,
    label: str,
    endpoint: str,
    status_code: int,
    payload_bytes: bytes | None,
    cache_hit: bool,
    request_params: dict[str, str | int | bool] | None = None,
) -> dict[str, object]:
    base: dict[str, object] = {
        "label": label,
        "endpoint": endpoint,
        "status_code": status_code,
        "access_result": (
            "ACCESSIBLE"
            if 200 <= status_code < 300
            else "AUTHENTICATION_FAILED"
            if status_code == 401
            else "NOT_ENTITLED"
            if status_code in {402, 403}
            else "UNAVAILABLE"
        ),
        "cache_hit": cache_hit,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest() if payload_bytes else None,
        "row_count": 0,
        "envelope_fields": [],
        "row_fields": [],
        "timestamp_fields": [],
        "identity_fields": [],
        "title_or_summary_available": False,
        "full_text_available": False,
        "observed_min_date": None,
        "observed_max_date": None,
        "metadata_only": None,
        "production_exposure": None,
        "public_exposure": None,
        "source_attribution_required": None,
        "requested_filter_names": sorted((request_params or {}).keys()),
        "raw_values_excluded_from_report": True,
    }
    if not payload_bytes or not 200 <= status_code < 300:
        return base
    payload = json.loads(payload_bytes)
    rows = _extract_rows(payload)
    envelope_fields = sorted(payload) if isinstance(payload, dict) else []
    row_fields = sorted({field for row in rows for field in row})
    timestamp_values = sorted(
        str(row[field])[:10]
        for row in rows
        for field in TIMESTAMP_FIELDS
        if field != "event_time" and row.get(field) not in (None, "")
    )
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    if not isinstance(meta, dict):
        meta = {}
    base.update(
        {
            "row_count": len(rows),
            "envelope_fields": envelope_fields,
            "row_fields": row_fields,
            "timestamp_fields": sorted(TIMESTAMP_FIELDS & set(row_fields)),
            "identity_fields": sorted(IDENTITY_FIELDS & set(row_fields)),
            "title_or_summary_available": any(_has_nonempty(row, TITLE_FIELDS) for row in rows),
            "full_text_available": any(_has_nonempty(row, FULL_TEXT_FIELDS) for row in rows),
            "observed_min_date": timestamp_values[0] if timestamp_values else None,
            "observed_max_date": timestamp_values[-1] if timestamp_values else None,
            "metadata_only": meta.get("metadata_only"),
            "production_exposure": meta.get("production_exposure"),
            "public_exposure": meta.get("public_exposure"),
            "source_attribution_required": meta.get("source_attribution_required"),
        }
    )
    return base


def run_audit(
    config: TwmdProReauditConfig,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    output_path: Path = DEFAULT_OUTPUT,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    credential = load_api_key(config.api_key_environment_variable)
    headers = {
        "X-API-Key": credential,
        "User-Agent": "financial-ai-assistant/0.1 twmd-pro-bounded-reaudit",
    }
    results: list[dict[str, object]] = []
    with httpx.Client(
        headers=headers,
        timeout=httpx.Timeout(config.timeout_seconds, connect=10.0),
        follow_redirects=True,
    ) as client:
        for probe in config.probes:
            cache_path = cache_dir / f"{probe.label}.json"
            cache_hit = cache_path.exists()
            if cache_hit:
                payload_bytes = cache_path.read_bytes()
                status_code = 200
            else:
                response = client.get(str(probe.endpoint), params=probe.params)
                status_code = response.status_code
                payload_bytes = response.content if not response.is_error else None
                if payload_bytes and len(payload_bytes) > config.max_response_bytes:
                    raise ValueError(f"{probe.label} exceeded max_response_bytes")
                if payload_bytes:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(payload_bytes)
            results.append(
                summarize_payload(
                    label=probe.label,
                    endpoint=str(probe.endpoint),
                    status_code=status_code,
                    payload_bytes=payload_bytes,
                    cache_hit=cache_hit,
                    request_params=probe.params,
                )
            )
    statuses = [int(result["status_code"]) for result in results]
    any_accessible = any(200 <= status < 300 for status in statuses)
    if any_accessible:
        for result in results:
            if result["status_code"] == 401:
                result["access_result"] = "NOT_ENTITLED_OR_PRIVATE_BETA"
    report = {
        "audit_version": config.audit_version,
        "retrieved_at": (retrieved_at or datetime.now(UTC)).isoformat(),
        "request_count": len(results),
        "maximum_rows_requested_per_call": 2,
        "authentication_result": (
            "CONFIRMED"
            if any_accessible
            else "FAILED"
            if 401 in statuses
            else "INCONCLUSIVE"
        ),
        "api_key_recorded": False,
        "raw_content_committed": False,
        "local_cache_path": str(cache_dir),
        "results": results,
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if re.search(r"(?:sk_live_|TWMD_API_KEY=)", serialized):
        raise RuntimeError("credential-like material detected in public audit output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bounded TWMD Pro entitlement re-audit.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_audit(load_config(args.config), cache_dir=args.cache_dir, output_path=args.output)
    safe_statuses = [
        (item["label"], item["status_code"], item["row_count"])
        for item in report["results"]
    ]
    print(f"TWMD Pro bounded re-audit complete: {safe_statuses}")


if __name__ == "__main__":
    main()
