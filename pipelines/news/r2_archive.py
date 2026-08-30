from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from pipelines.news.b2_forward import run_id_for

TAIPEI = ZoneInfo("Asia/Taipei")
SOURCE_KEY = {
    "twse_openapi_daily_material": "twse",
    "tpex_openapi_daily_material": "tpex",
}


class R2ConfigurationError(RuntimeError):
    pass


class R2ImmutableCollisionError(RuntimeError):
    pass


class S3Body(Protocol):
    def read(self) -> bytes: ...


class S3Client(Protocol):
    def head_bucket(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> dict[str, object]: ...

    def put_object(self, **kwargs: object) -> object: ...


@dataclass(frozen=True)
class R2Settings:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    endpoint: str
    prefix: str = "forward-events"
    private_confirmed: bool = False

    @classmethod
    def from_env(cls) -> R2Settings:
        values = {
            name: os.getenv(name, "").strip()
            for name in (
                "R2_ACCOUNT_ID",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
                "R2_BUCKET_NAME",
                "R2_ENDPOINT",
            )
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise R2ConfigurationError(
                "missing required R2 configuration names: " + ", ".join(missing)
            )
        return cls(
            account_id=values["R2_ACCOUNT_ID"],
            access_key_id=values["R2_ACCESS_KEY_ID"],
            secret_access_key=values["R2_SECRET_ACCESS_KEY"],
            bucket_name=values["R2_BUCKET_NAME"],
            endpoint=values["R2_ENDPOINT"],
            prefix=os.getenv("R2_PREFIX", "forward-events").strip("/ "),
            private_confirmed=os.getenv("R2_BUCKET_PRIVATE_CONFIRMED", "").lower()
            == "true",
        )

    def validate(self) -> None:
        expected = f"https://{self.account_id}.r2.cloudflarestorage.com"
        if self.endpoint.rstrip("/") != expected:
            raise R2ConfigurationError("R2 endpoint does not match the configured account ID")
        if not self.prefix:
            raise R2ConfigurationError("R2_PREFIX cannot be empty")
        if not self.private_confirmed:
            raise R2ConfigurationError(
                "R2 bucket privacy must be verified before collection"
            )


def build_r2_client(settings: R2Settings) -> S3Client:
    settings.validate()
    try:
        import boto3
    except ImportError as error:
        raise R2ConfigurationError(
            "R2 deployment requires the optional 'forward' dependency"
        ) from error
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name="auto",
    )


class R2ForwardArchive:
    def __init__(self, settings: R2Settings, *, client: S3Client | None = None) -> None:
        settings.validate()
        self.settings = settings
        self.client = client or build_r2_client(settings)

    def verify_access(self) -> None:
        self.client.head_bucket(Bucket=self.settings.bucket_name)

    def load_manifest(
        self, *, phase: str, observed_at: datetime
    ) -> dict[str, object] | None:
        key = self.manifest_key(phase=phase, observed_at=observed_at)
        payload = self._get_optional(key)
        if payload is None:
            return None
        manifest = json.loads(payload)
        expected = _manifest_digest(manifest)
        if manifest.get("manifest_sha256") != expected:
            raise R2ImmutableCollisionError("remote run manifest failed its SHA-256 check")
        return manifest

    def upload_run(self, *, root: Path, manifest: dict[str, object]) -> None:
        if manifest.get("status") != "SUCCESS":
            raise ValueError("only successful runs can be finalized in the R2 archive")
        observed_at = datetime.fromisoformat(str(manifest["observed_at"]))
        run_id = str(manifest["run_id"])
        collection_date = observed_at.astimezone(TAIPEI).date().isoformat()
        sources = manifest.get("sources")
        if not isinstance(sources, list):
            raise ValueError("run manifest sources must be a list")
        for source in sources:
            if not isinstance(source, dict) or source.get("status") != "SUCCESS":
                raise ValueError("run manifest contains a non-success source")
            source_id = str(source["source_id"])
            source_name = SOURCE_KEY[source_id]
            base = (
                f"{self.settings.prefix}/source={source_name}/date={collection_date}/"
                f"run={run_id}"
            )
            raw_ref = str(source["raw_payload_ref"])
            raw_path = root / raw_ref
            self._put_immutable(
                f"{base}/raw/{raw_path.name}",
                raw_path.read_bytes(),
                content_type=str(source["content_type"]),
            )
            version_ids = source.get("document_version_ids")
            if not isinstance(version_ids, list):
                raise ValueError("source document_version_ids must be a list")
            for version_id in version_ids:
                path = root / "normalized" / source_id / f"{version_id}.json"
                self._put_immutable(
                    f"{base}/normalized/{version_id}.json",
                    path.read_bytes(),
                    content_type="application/json",
                )
            source_manifest = {
                "run_id": run_id,
                "phase": manifest["phase"],
                "observed_at": manifest["observed_at"],
                "source": source,
                "automatic_retraining": False,
            }
            self._put_immutable(
                f"{base}/manifest/source.json",
                _json_bytes(source_manifest),
                content_type="application/json",
            )
        self._put_immutable(
            self.manifest_key(phase=str(manifest["phase"]), observed_at=observed_at),
            _json_bytes(manifest),
            content_type="application/json",
        )

    def manifest_key(self, *, phase: str, observed_at: datetime) -> str:
        collection_date = observed_at.astimezone(TAIPEI).date().isoformat()
        run_id = run_id_for(phase, observed_at)
        return (
            f"{self.settings.prefix}/runs/date={collection_date}/phase={phase}/"
            f"run={run_id}/manifest.json"
        )

    def _put_immutable(self, key: str, payload: bytes, *, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.settings.bucket_name,
                Key=key,
                Body=payload,
                ContentType=content_type,
                Metadata={"sha256": hashlib.sha256(payload).hexdigest()},
                IfNoneMatch="*",
            )
        except Exception as error:  # noqa: BLE001 - SDK error types are optional dependencies
            if not _has_error_code(error, {"PreconditionFailed", "412"}):
                raise
            existing = self._get_optional(key)
            if existing != payload:
                raise R2ImmutableCollisionError(
                    "remote immutable object already exists with different content"
                ) from error

    def _get_optional(self, key: str) -> bytes | None:
        try:
            response = self.client.get_object(Bucket=self.settings.bucket_name, Key=key)
        except Exception as error:  # noqa: BLE001 - SDK error types are optional dependencies
            if _has_error_code(error, {"NoSuchKey", "404", "NotFound"}):
                return None
            raise
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise R2ImmutableCollisionError("R2 object body is unavailable")
        return body.read()


def _manifest_digest(manifest: dict[str, object]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(
        json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _has_error_code(error: Exception, codes: set[str]) -> bool:
    response = getattr(error, "response", {})
    if not isinstance(response, dict):
        return False
    details = response.get("Error", {})
    if not isinstance(details, dict):
        return False
    return str(details.get("Code")) in codes


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
