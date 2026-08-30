import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from jobs.b2_forward_r2 import canonical_observed_at, execute_r2_collection
from pipelines.news.b2_dataset import load_b2_contract
from pipelines.news.b2_forward import run_id_for
from pipelines.news.r2_archive import (
    R2ConfigurationError,
    R2ForwardArchive,
    R2ImmutableCollisionError,
    R2Settings,
)


class FakeS3Error(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_attempts = 0
        self.head_calls = 0

    def head_bucket(self, **kwargs: object) -> None:
        assert kwargs["Bucket"] == "private-forward-events"
        self.head_calls += 1

    def get_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise FakeS3Error("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[key])}

    def put_object(self, **kwargs: object) -> None:
        self.put_attempts += 1
        key = str(kwargs["Key"])
        payload = kwargs["Body"]
        assert isinstance(payload, bytes)
        if kwargs.get("IfNoneMatch") == "*" and key in self.objects:
            raise FakeS3Error("PreconditionFailed")
        self.objects[key] = payload


def _settings(*, private: bool = True) -> R2Settings:
    return R2Settings(
        account_id="account-id",
        access_key_id="access-key",
        secret_access_key="secret-key",
        bucket_name="private-forward-events",
        endpoint="https://account-id.r2.cloudflarestorage.com",
        private_confirmed=private,
    )


def _manifest(root: Path, observed_at: datetime) -> dict[str, object]:
    sources: list[dict[str, object]] = []
    for source_id, short_name in (
        ("twse_openapi_daily_material", "twse"),
        ("tpex_openapi_daily_material", "tpex"),
    ):
        raw = f"{short_name}-raw".encode()
        raw_sha = hashlib.sha256(raw).hexdigest()
        raw_ref = f"raw/{source_id}/2026/08/30/{raw_sha}.bin"
        raw_path = root / raw_ref
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
        version_id = hashlib.sha256(f"{source_id}-version".encode()).hexdigest()
        normalized = root / "normalized" / source_id / f"{version_id}.json"
        normalized.parent.mkdir(parents=True, exist_ok=True)
        normalized.write_text('{"safe":true}\n')
        sources.append(
            {
                "source_id": source_id,
                "status": "SUCCESS",
                "content_type": "application/json",
                "raw_sha256": raw_sha,
                "raw_payload_ref": raw_ref,
                "document_version_ids": [version_id],
            }
        )
    manifest: dict[str, object] = {
        "schema_version": "b2-forward-event-run-manifest-v1",
        "runner_version": "b2-private-forward-event-runner-v1",
        "contract_version": "b2-taiwan-financial-text-v1",
        "run_id": run_id_for("current", observed_at),
        "phase": "current",
        "observed_at": observed_at.isoformat(),
        "status": "SUCCESS",
        "successful_source_count": 2,
        "sources": sources,
        "automatic_retraining": False,
    }
    unsigned = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    manifest["manifest_sha256"] = hashlib.sha256(unsigned).hexdigest()
    return manifest


def test_r2_settings_require_exact_endpoint_and_private_confirmation() -> None:
    _settings().validate()
    with pytest.raises(R2ConfigurationError, match="privacy"):
        _settings(private=False).validate()
    invalid = _settings()
    invalid = R2Settings(**{**invalid.__dict__, "endpoint": "https://example.test"})
    with pytest.raises(R2ConfigurationError, match="account ID"):
        invalid.validate()


def test_canonical_phase_times_match_frozen_utc_schedule() -> None:
    selected_date = date(2026, 8, 30)
    assert canonical_observed_at("next_morning", selected_date).isoformat() == (
        "2026-08-30T00:00:00+00:00"
    )
    assert canonical_observed_at("current", selected_date).isoformat() == (
        "2026-08-30T08:30:00+00:00"
    )
    assert canonical_observed_at("evening", selected_date).isoformat() == (
        "2026-08-30T13:30:00+00:00"
    )


def test_r2_archive_writes_private_source_date_run_layout_immutably(tmp_path: Path) -> None:
    client = FakeS3Client()
    archive = R2ForwardArchive(_settings(), client=client)
    observed_at = datetime(2026, 8, 30, 8, 30, tzinfo=UTC)
    manifest = _manifest(tmp_path, observed_at)

    archive.upload_run(root=tmp_path, manifest=manifest)
    original_objects = dict(client.objects)
    archive.upload_run(root=tmp_path, manifest=manifest)

    assert client.objects == original_objects
    keys = set(client.objects)
    assert any("source=twse/date=2026-08-30/run=" in key for key in keys)
    assert any("source=tpex/date=2026-08-30/run=" in key for key in keys)
    assert any(key.endswith("/manifest.json") for key in keys)
    loaded = archive.load_manifest(phase="current", observed_at=observed_at)
    assert loaded == manifest


def test_remote_manifest_prevents_second_provider_run(tmp_path: Path) -> None:
    client = FakeS3Client()
    archive = R2ForwardArchive(_settings(), client=client)
    observed_at = datetime(2026, 8, 30, 8, 30, tzinfo=UTC)
    manifest = _manifest(tmp_path, observed_at)
    archive.upload_run(root=tmp_path, manifest=manifest)

    def forbidden_runner(contract: object, root: Path) -> object:
        raise AssertionError("provider runner must not be constructed")

    returned, reused = execute_r2_collection(
        contract=load_b2_contract(),
        archive=archive,
        phase="current",
        observed_at=observed_at,
        runner_factory=forbidden_runner,
    )

    assert reused is True
    assert returned == manifest
    assert client.head_calls == 1


def test_r2_archive_rejects_different_content_at_immutable_key(tmp_path: Path) -> None:
    client = FakeS3Client()
    archive = R2ForwardArchive(_settings(), client=client)
    observed_at = datetime(2026, 8, 30, 8, 30, tzinfo=UTC)
    manifest = _manifest(tmp_path, observed_at)
    archive.upload_run(root=tmp_path, manifest=manifest)
    raw_key = next(key for key in client.objects if "/raw/" in key)
    client.objects[raw_key] = b"different"

    with pytest.raises(R2ImmutableCollisionError, match="different content"):
        archive.upload_run(root=tmp_path, manifest=manifest)
