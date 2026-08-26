from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

MANIFEST_VERSION = "taiwan-active-source-manifest-v1"
REPORT_VERSION = "taiwan-source-gate-report-v1"
DEFAULT_MANIFEST = Path("research/configs/taiwan_active_sources.v1.json")
DEFAULT_OUTPUT = Path("artifacts/taiwan-source-gate-report.json")
SENSITIVE_QUERY_MARKERS = ("token", "secret", "password", "key", "credential", "auth")


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    purpose: str = Field(min_length=1, max_length=300)
    decision: Literal["ACCEPT"] = "ACCEPT"
    endpoint: HttpUrl
    terms_url: HttpUrl
    http_method: Literal["GET", "HEAD"] = "GET"
    response_container: Literal["root_list", "data", "headers_only"]
    query: dict[str, str] = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)
    required_headers: list[str] = Field(default_factory=list)
    date_field: str | None = None
    expected_content_type: str | None = None
    timezone_contract: str = Field(min_length=1, max_length=200)
    retention_policy: Literal["metadata_hash_only"] = "metadata_hash_only"
    allowed_uses: list[str] = Field(min_length=1)
    forbidden_uses: list[str] = Field(min_length=1)
    max_response_bytes: int = Field(default=5_000_000, ge=1, le=10_000_000)
    max_content_length_bytes: int | None = Field(default=None, ge=1, le=50_000_000)

    @field_validator("query")
    @classmethod
    def reject_sensitive_query_parameters(cls, value: dict[str, str]) -> dict[str, str]:
        for key in value:
            lowered = key.casefold()
            if any(marker in lowered for marker in SENSITIVE_QUERY_MARKERS):
                raise ValueError(f"sensitive query parameter is forbidden: {key}")
        return value

    @field_validator("required_fields", "required_headers")
    @classmethod
    def require_unique_names(cls, value: list[str]) -> list[str]:
        normalized = [field.strip() for field in value]
        if any(not field for field in normalized):
            raise ValueError("required names cannot contain empty values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("required names must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_date_field(self) -> SourceDefinition:
        if self.date_field and self.date_field not in self.required_fields:
            raise ValueError("date_field must also be listed in required_fields")
        if self.response_container == "headers_only":
            if self.http_method != "HEAD":
                raise ValueError("headers_only sources must use HEAD")
            if not self.required_headers:
                raise ValueError("headers_only sources require required_headers")
            if self.required_fields or self.date_field:
                raise ValueError("headers_only sources cannot define row fields")
        else:
            if self.http_method != "GET":
                raise ValueError("JSON row sources must use GET")
            if not self.required_fields:
                raise ValueError("JSON row sources require required_fields")
        return self


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    manifest_version: Literal["taiwan-active-source-manifest-v1"] = MANIFEST_VERSION
    sources: list[SourceDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_source_ids(self) -> SourceManifest:
        source_ids = [source.source_id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_id values must be unique")
        return self


def load_manifest(path: Path) -> SourceManifest:
    return SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))


def run_source_gates(
    manifest: SourceManifest,
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
        headers={"User-Agent": "financial-ai-assistant/0.1 source-audit"},
    )
    try:
        observations = [
            _observe_source(source, active_client, observed_at) for source in manifest.sources
        ]
    finally:
        if owns_client:
            active_client.close()

    content_lengths = [
        item["content_length_bytes"]
        for item in observations
        if isinstance(item.get("content_length_bytes"), int)
    ]
    return {
        "report_version": REPORT_VERSION,
        "manifest_version": manifest.manifest_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "overall_passed": all(item["passed"] for item in observations),
        "source_count": len(observations),
        "headers_only_source_count": sum(
            source.response_container == "headers_only" for source in manifest.sources
        ),
        "total_content_length_bytes": sum(content_lengths),
        "observations": observations,
        "raw_content_stored": False,
    }


def _observe_source(
    source: SourceDefinition,
    client: httpx.Client,
    retrieved_at: datetime,
) -> dict[str, object]:
    base = {
        "source_id": source.source_id,
        "purpose": source.purpose,
        "decision": source.decision,
        "endpoint": str(source.endpoint),
        "terms_url": str(source.terms_url),
        "http_method": source.http_method,
        "dataset_id": source.query.get("dataset"),
        "data_id": source.query.get("data_id"),
        "requested_start_date": source.query.get("start_date"),
        "requested_end_date": source.query.get("end_date"),
        "timezone_contract": source.timezone_contract,
        "retention_policy": source.retention_policy,
        "retrieved_at": retrieved_at.astimezone(UTC).isoformat(),
        "raw_content_stored": False,
    }
    try:
        response = client.request(source.http_method, str(source.endpoint), params=source.query)
        response.raise_for_status()
        if source.response_container == "headers_only":
            return _observe_headers(source, response, base)
        if len(response.content) > source.max_response_bytes:
            raise ValueError("response exceeded manifest max_response_bytes")
        payload = response.json()
        rows = _extract_rows(payload, source.response_container)
        observed_fields = sorted({str(key).strip() for row in rows for key in row})
        required_fields = sorted(source.required_fields)
        missing_fields = sorted(set(required_fields) - set(observed_fields))
        issues = []
        if not rows:
            issues.append("empty_response")
        if missing_fields:
            issues.append("missing_required_fields")
        date_values = _date_range(rows, source.date_field)
        canonical_payload = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        schema_payload = json.dumps(
            observed_fields, ensure_ascii=False, separators=(",", ":")
        ).encode()
        return {
            **base,
            "passed": not issues,
            "http_status": response.status_code,
            "record_count": len(rows),
            "observed_fields": observed_fields,
            "required_fields": required_fields,
            "missing_fields": missing_fields,
            "observed_min_date": date_values[0],
            "observed_max_date": date_values[1],
            "snapshot_sha256": hashlib.sha256(canonical_payload).hexdigest(),
            "schema_sha256": hashlib.sha256(schema_payload).hexdigest(),
            "issues": issues,
            "error_code": None,
        }
    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as error:
        status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        return {
            **base,
            "passed": False,
            "http_status": status,
            "record_count": 0,
            "observed_fields": [],
            "required_fields": sorted(source.required_fields),
            "missing_fields": sorted(source.required_fields),
            "observed_headers": [],
            "required_headers": sorted(header.casefold() for header in source.required_headers),
            "missing_headers": sorted(header.casefold() for header in source.required_headers),
            "content_length_bytes": None,
            "content_type": None,
            "last_modified": None,
            "etag_sha256": None,
            "observed_min_date": None,
            "observed_max_date": None,
            "snapshot_sha256": None,
            "schema_sha256": None,
            "issues": ["source_observation_failed"],
            "error_code": type(error).__name__,
        }


def _observe_headers(
    source: SourceDefinition,
    response: httpx.Response,
    base: dict[str, object],
) -> dict[str, object]:
    headers = {key.casefold(): value.strip() for key, value in response.headers.items()}
    required_headers = sorted(header.casefold() for header in source.required_headers)
    missing_headers = sorted(set(required_headers) - set(headers))
    issues = []
    if missing_headers:
        issues.append("missing_required_headers")

    content_length = _content_length(headers.get("content-length"))
    if content_length is None or content_length <= 0:
        issues.append("invalid_content_length")
    if (
        content_length is not None
        and source.max_content_length_bytes is not None
        and content_length > source.max_content_length_bytes
    ):
        issues.append("content_length_exceeded")

    content_type = headers.get("content-type")
    if source.expected_content_type and (
        not content_type
        or not content_type.casefold().startswith(source.expected_content_type.casefold())
    ):
        issues.append("unexpected_content_type")

    retained_headers = {header: headers.get(header) for header in required_headers}
    canonical_headers = json.dumps(
        retained_headers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    observed_headers = sorted(headers)
    schema_payload = json.dumps(observed_headers, separators=(",", ":")).encode()
    etag = headers.get("etag")
    return {
        **base,
        "passed": not issues,
        "http_status": response.status_code,
        "record_count": None,
        "observed_fields": [],
        "required_fields": [],
        "missing_fields": [],
        "observed_headers": observed_headers,
        "required_headers": required_headers,
        "missing_headers": missing_headers,
        "content_length_bytes": content_length,
        "content_type": content_type,
        "last_modified": headers.get("last-modified"),
        "etag_sha256": hashlib.sha256(etag.encode()).hexdigest() if etag else None,
        "observed_min_date": None,
        "observed_max_date": None,
        "snapshot_sha256": hashlib.sha256(canonical_headers).hexdigest(),
        "schema_sha256": hashlib.sha256(schema_payload).hexdigest(),
        "issues": issues,
        "error_code": None,
    }


def _content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _extract_rows(payload: object, container: str) -> list[dict[str, object]]:
    if container == "root_list":
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data")
    else:
        rows = None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise TypeError("source response did not contain the configured row list")
    return rows


def _date_range(
    rows: list[dict[str, object]], date_field: str | None
) -> tuple[str | None, str | None]:
    if not date_field:
        return None, None
    values = sorted(str(row[date_field]).strip() for row in rows if row.get(date_field))
    return (values[0], values[-1]) if values else (None, None)


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run metadata-only gates for accepted Taiwan research sources"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_source_gates(load_manifest(args.manifest))
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "overall_passed": report["overall_passed"],
                "source_count": report["source_count"],
                "headers_only_source_count": report["headers_only_source_count"],
                "total_content_length_bytes": report["total_content_length_bytes"],
                "raw_content_stored": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["overall_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
