from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pipelines.news.b2_dataset import (
    B2Contract,
    SourceCollectionContract,
    normalize_news_item,
    persist_document_versions,
    persist_raw_snapshot,
)
from pipelines.news.tpex_material import TpexMaterialAnnouncementProvider
from pipelines.news.twse_material import TwseMaterialAnnouncementProvider
from pipelines.news.types import NewsItem, NewsProviderPayload

RUNNER_VERSION = "b2-private-forward-event-runner-v1"
DEFAULT_PRIVATE_ROOT = Path(".tools/private/b2-forward-events-v1")
SOURCE_IDS = (
    "twse_openapi_daily_material",
    "tpex_openapi_daily_material",
)
PHASE_SCHEDULE = {
    "current": "16:30",
    "evening": "21:30",
    "next_morning": "08:00+1d",
}


class BatchProvider(Protocol):
    endpoint: str

    def fetch_raw(self) -> NewsProviderPayload: ...

    def parse_raw(self, payload: NewsProviderPayload) -> tuple[NewsItem, ...]: ...


ProviderFactory = Callable[[], AbstractContextManager[BatchProvider]]


class ForwardCollectionLockedError(RuntimeError):
    pass


class ForwardCollectionRunError(RuntimeError):
    def __init__(self, manifest: dict[str, object]) -> None:
        super().__init__("one or more official sources failed; inspect the private run manifest")
        self.manifest = manifest


def default_provider_factories(contract: B2Contract) -> dict[str, ProviderFactory]:
    source_contracts = {source.source_id: source for source in contract.sources}
    twse = source_contracts["twse_openapi_daily_material"]
    tpex = source_contracts["tpex_openapi_daily_material"]
    return {
        "twse_openapi_daily_material": lambda: TwseMaterialAnnouncementProvider(
            max_retries=twse.max_attempts,
            backoff_seconds=tuple(twse.backoff_seconds),
        ),
        "tpex_openapi_daily_material": lambda: TpexMaterialAnnouncementProvider(
            max_retries=tpex.max_attempts,
            backoff_seconds=tuple(tpex.backoff_seconds),
        ),
    }


class B2ForwardEventRunner:
    def __init__(
        self,
        contract: B2Contract,
        *,
        root: Path = DEFAULT_PRIVATE_ROOT,
        provider_factories: Mapping[str, ProviderFactory] | None = None,
    ) -> None:
        self.contract = contract
        self.root = root
        self.source_contracts = {source.source_id: source for source in contract.sources}
        self.provider_factories = dict(
            provider_factories or default_provider_factories(contract)
        )
        if tuple(self.provider_factories) != SOURCE_IDS:
            raise ValueError("forward runner must contain exactly the frozen TWSE/TPEx sources")
        expected_schedule = list(PHASE_SCHEDULE.values())
        for source_id in SOURCE_IDS:
            if self.source_contracts[source_id].schedule != expected_schedule:
                raise ValueError("forward runner phases must match the frozen B2 schedule")

    def run(
        self,
        *,
        phase: str,
        observed_at: datetime | None = None,
        scheduler_deployed: bool = False,
    ) -> dict[str, object]:
        if phase not in PHASE_SCHEDULE:
            raise ValueError(f"unsupported reconciliation phase: {phase}")
        run_at = observed_at or datetime.now(UTC)
        if run_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        with _single_run_lock(self.root, run_at):
            manifest = _load_manifest(self.root, phase, run_at)
            if manifest is None:
                manifest = self._collect(
                    phase=phase,
                    observed_at=run_at,
                    scheduler_deployed=scheduler_deployed,
                )
                _persist_manifest(self.root, manifest)
        if manifest["status"] != "SUCCESS":
            raise ForwardCollectionRunError(manifest)
        return manifest

    def _collect(
        self,
        *,
        phase: str,
        observed_at: datetime,
        scheduler_deployed: bool,
    ) -> dict[str, object]:
        source_results: list[dict[str, object]] = []
        for source_id in SOURCE_IDS:
            try:
                source_results.append(
                    self._collect_source(
                        source_id=source_id,
                        source_contract=self.source_contracts[source_id],
                        observed_at=observed_at,
                    )
                )
            except Exception as error:  # noqa: BLE001 - manifest must record partial source failure
                source_results.append(
                    {
                        "source_id": source_id,
                        "status": "FAILED",
                        "error_type": type(error).__name__,
                    }
                )
        success_count = sum(row["status"] == "SUCCESS" for row in source_results)
        status = "SUCCESS" if success_count == len(SOURCE_IDS) else "PARTIAL_OR_FAILED"
        manifest: dict[str, object] = {
            "schema_version": "b2-forward-event-run-manifest-v1",
            "runner_version": RUNNER_VERSION,
            "contract_version": self.contract.contract_version,
            "run_id": run_id_for(phase, observed_at),
            "phase": phase,
            "contract_schedule": PHASE_SCHEDULE[phase],
            "observed_at": observed_at.astimezone(UTC).isoformat(),
            "status": status,
            "source_count": len(SOURCE_IDS),
            "successful_source_count": success_count,
            "sources": source_results,
            "automatic_retraining": False,
            "scheduler_deployed": scheduler_deployed,
            "raw_payload_public": False,
        }
        manifest["manifest_sha256"] = _manifest_sha256(manifest)
        return manifest

    def _collect_source(
        self,
        *,
        source_id: str,
        source_contract: SourceCollectionContract,
        observed_at: datetime,
    ) -> dict[str, object]:
        factory = self.provider_factories[source_id]
        with factory() as provider:
            payload = provider.fetch_raw()
            raw = persist_raw_snapshot(
                source_id=source_id,
                raw_content_kind="OFFICIAL_OPEN_DATA",
                raw_payload=payload.raw_payload,
                root=self.root,
                observed_at=observed_at,
            )
            items = provider.parse_raw(payload)
            documents = [
                normalize_news_item(
                    source_id=source_id,
                    source_type="OFFICIAL_ANNOUNCEMENT",
                    provider=("TWSE" if source_id.startswith("twse_") else "TPEx"),
                    item=item,
                    raw_payload_ref=raw.reference,
                    ingestion_timestamp=observed_at,
                )
                for item in items
            ]
            persist_document_versions(
                source_id=source_id,
                documents=documents,
                root=self.root,
            )
        version_ids = sorted(document.document_version_id for document in documents)
        publication_times = sorted(document.publication_timestamp for document in documents)
        return {
            "source_id": source_id,
            "status": "SUCCESS",
            "endpoint": provider.endpoint,
            "content_type": payload.content_type,
            "row_count": len(documents),
            "raw_sha256": raw.sha256,
            "raw_payload_ref": raw.reference,
            "document_versions_sha256": _sha256_json(version_ids),
            "document_version_ids": version_ids,
            "min_publication_timestamp": (
                publication_times[0].isoformat() if publication_times else None
            ),
            "max_publication_timestamp": (
                publication_times[-1].isoformat() if publication_times else None
            ),
            "timestamp_semantics": "official announcement publication time",
            "timezone": "Asia/Taipei",
            "max_attempts": source_contract.max_attempts,
            "backoff_seconds": source_contract.backoff_seconds,
        }


@contextmanager
def _single_run_lock(root: Path, observed_at: datetime):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".collector.lock"
    payload = json.dumps(
        {
            "runner_version": RUNNER_VERSION,
            "started_at": observed_at.astimezone(UTC).isoformat(),
        },
        sort_keys=True,
    ).encode()
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ForwardCollectionLockedError(
            "another forward collection run holds the lock"
        ) from error
    try:
        os.write(descriptor, payload)
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock_path.unlink(missing_ok=True)


def _persist_manifest(root: Path, manifest: dict[str, object]) -> None:
    observed_at = datetime.fromisoformat(str(manifest["observed_at"]))
    path = _manifest_path(root, str(manifest["phase"]), observed_at)
    payload = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError("refusing to overwrite a different immutable run manifest")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _load_manifest(
    root: Path, phase: str, observed_at: datetime
) -> dict[str, object] | None:
    path = _manifest_path(root, phase, observed_at)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("manifest_sha256") != _manifest_sha256_without_digest(payload):
        raise ValueError("existing immutable run manifest failed its lineage hash check")
    return payload


def _manifest_path(root: Path, phase: str, observed_at: datetime) -> Path:
    date_path = observed_at.astimezone(UTC).strftime("%Y/%m/%d")
    return root / "manifests" / date_path / f"{run_id_for(phase, observed_at)}.json"


def run_id_for(phase: str, observed_at: datetime) -> str:
    return hashlib.sha256(
        f"{RUNNER_VERSION}\x1f{phase}\x1f{observed_at.astimezone(UTC).isoformat()}".encode()
    ).hexdigest()[:24]


def _manifest_sha256(manifest: dict[str, object]) -> str:
    return _sha256_json(manifest)


def _manifest_sha256_without_digest(manifest: dict[str, object]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return _manifest_sha256(unsigned)


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
