from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research.evaluation.source_manifest import SourceManifest, load_manifest, run_source_gates


def _manifest() -> SourceManifest:
    return SourceManifest.model_validate(
        {
            "manifest_version": "taiwan-active-source-manifest-v1",
            "sources": [
                {
                    "source_id": "twse_test_source",
                    "purpose": "synthetic TWSE metadata gate",
                    "endpoint": "https://example.test/twse",
                    "terms_url": "https://example.test/terms",
                    "response_container": "root_list",
                    "required_fields": ["發言日期", "發言時間", "公司代號", "主旨"],
                    "date_field": "發言日期",
                    "timezone_contract": "Asia/Taipei",
                    "allowed_uses": ["metadata"],
                    "forbidden_uses": ["raw text persistence"],
                },
                {
                    "source_id": "taiex_test_source",
                    "purpose": "synthetic benchmark gate",
                    "endpoint": "https://example.test/taiex",
                    "terms_url": "https://example.test/terms",
                    "response_container": "data",
                    "query": {
                        "dataset": "TaiwanStockTotalReturnIndex",
                        "data_id": "TAIEX",
                        "start_date": "2026-08-03",
                        "end_date": "2026-08-08",
                    },
                    "required_fields": ["price", "stock_id", "date"],
                    "date_field": "date",
                    "timezone_contract": "Asia/Taipei trading date",
                    "allowed_uses": ["research benchmark"],
                    "forbidden_uses": ["sentiment truth"],
                },
            ],
        }
    )


def test_source_gate_passes_and_never_emits_raw_content() -> None:
    forbidden_title = "這段公告原文不得進入報告"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/twse":
            return httpx.Response(
                200,
                json=[
                    {
                        "發言日期": "1150826",
                        "發言時間": "090000",
                        "公司代號": "0000",
                        "主旨": forbidden_title,
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "status": 200,
                "data": [
                    {"price": 100.0, "stock_id": "TAIEX", "date": "2026-08-03"},
                    {"price": 101.0, "stock_id": "TAIEX", "date": "2026-08-04"},
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_source_gates(
            _manifest(), client=client, retrieved_at=datetime(2026, 8, 26, tzinfo=UTC)
        )

    assert report["overall_passed"] is True
    assert report["raw_content_stored"] is False
    assert [item["record_count"] for item in report["observations"]] == [1, 2]
    assert report["observations"][1]["observed_min_date"] == "2026-08-03"
    assert report["observations"][1]["observed_max_date"] == "2026-08-04"
    assert forbidden_title not in str(report)


def test_source_gate_fails_when_required_schema_is_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/twse":
            return httpx.Response(200, json=[{"發言日期": "1150826"}])
        return httpx.Response(200, json={"data": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_source_gates(_manifest(), client=client)

    assert report["overall_passed"] is False
    assert "missing_required_fields" in report["observations"][0]["issues"]
    assert "empty_response" in report["observations"][1]["issues"]


def test_manifest_rejects_secrets_and_duplicate_source_ids() -> None:
    payload = _manifest().model_dump(mode="json")
    payload["sources"][0]["query"] = {"api_token": "not-a-real-secret"}
    with pytest.raises(ValidationError, match="sensitive query parameter"):
        SourceManifest.model_validate(payload)

    payload = _manifest().model_dump(mode="json")
    payload["sources"][1]["source_id"] = payload["sources"][0]["source_id"]
    with pytest.raises(ValidationError, match="source_id values must be unique"):
        SourceManifest.model_validate(payload)


def test_source_gate_requires_timezone_aware_observation_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        run_source_gates(_manifest(), retrieved_at=datetime(2026, 8, 26))


def test_committed_manifest_has_only_accepted_metadata_sources() -> None:
    manifest = load_manifest(Path("research/configs/taiwan_active_sources.v1.json"))

    assert [source.source_id for source in manifest.sources] == [
        "twse_material_metadata",
        "finmind_taiex_total_return",
    ]
    assert all(source.retention_policy == "metadata_hash_only" for source in manifest.sources)
    assert all(source.decision == "ACCEPT" for source in manifest.sources)


def test_headers_only_gate_uses_head_without_downloading_archive() -> None:
    manifest = SourceManifest.model_validate(
        {
            "sources": [
                {
                    "source_id": "fsc_test_archive",
                    "purpose": "synthetic FSC archive coverage",
                    "endpoint": "https://example.test/fsc.zip",
                    "terms_url": "https://example.test/terms",
                    "http_method": "HEAD",
                    "response_container": "headers_only",
                    "required_headers": [
                        "content-length",
                        "content-type",
                        "last-modified",
                        "etag",
                    ],
                    "expected_content_type": "application/x-zip-compressed",
                    "timezone_contract": "HTTP GMT only",
                    "allowed_uses": ["metadata coverage"],
                    "forbidden_uses": ["download"],
                    "max_response_bytes": 1,
                    "max_content_length_bytes": 3000000,
                }
            ]
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "HEAD"
        return httpx.Response(
            200,
            headers={
                "Content-Length": "224273",
                "Content-Type": "application/x-zip-compressed",
                "Last-Modified": "Tue, 25 Aug 2026 17:00:06 GMT",
                "ETag": '"synthetic-etag"',
            },
            content=b"",
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_source_gates(manifest, client=client)

    observation = report["observations"][0]
    assert report["overall_passed"] is True
    assert report["headers_only_source_count"] == 1
    assert report["total_content_length_bytes"] == 224273
    assert observation["content_length_bytes"] == 224273
    assert observation["record_count"] is None
    assert observation["raw_content_stored"] is False


def test_committed_fsc_manifest_is_headers_only() -> None:
    manifest = load_manifest(Path("research/configs/fsc_official_sources.v1.json"))

    assert len(manifest.sources) == 5
    assert all(source.http_method == "HEAD" for source in manifest.sources)
    assert all(source.response_container == "headers_only" for source in manifest.sources)
    assert all(
        "training before content audit" in source.forbidden_uses
        for source in manifest.sources
    )
