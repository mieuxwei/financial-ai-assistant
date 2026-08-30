import json
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pipelines.news.b2_dataset import load_b2_contract
from pipelines.news.b2_forward import (
    B2ForwardEventRunner,
    ForwardCollectionLockedError,
    ForwardCollectionRunError,
)
from pipelines.news.types import NewsItem, NewsProviderBatch, NewsProviderPayload


class FakeProvider(AbstractContextManager["FakeProvider"]):
    def __init__(
        self,
        *,
        endpoint: str,
        batch: NewsProviderBatch | None = None,
        parse_error: Exception | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.batch = batch
        self.parse_error = parse_error
        self.calls = 0

    def __enter__(self) -> "FakeProvider":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def fetch_raw(self) -> NewsProviderPayload:
        self.calls += 1
        assert self.batch is not None
        return NewsProviderPayload(
            raw_payload=self.batch.raw_payload,
            content_type=self.batch.content_type,
        )

    def parse_raw(self, payload: NewsProviderPayload) -> tuple[NewsItem, ...]:
        if self.parse_error is not None:
            raise self.parse_error
        assert self.batch is not None
        assert payload.raw_payload == self.batch.raw_payload
        return self.batch.items


def _batch(source: str, ticker: str, title: str) -> NewsProviderBatch:
    item = NewsItem(
        title=title,
        summary="公開說明",
        published_at=datetime.fromisoformat("2026-08-30T16:01:02+08:00"),
        source=source,
        source_type="official_announcement",
        url=f"https://example.test/{source}",
        external_id=f"{source}-{ticker}-1",
        explicit_tickers=(ticker,),
        metadata={"company_name": "測試公司", "clause": "第14款"},
    )
    raw = json.dumps({"source": source, "ticker": ticker}, sort_keys=True).encode()
    return NewsProviderBatch(raw_payload=raw, content_type="application/json", items=(item,))


def _runner(tmp_path: Path, twse: FakeProvider, tpex: FakeProvider) -> B2ForwardEventRunner:
    return B2ForwardEventRunner(
        load_b2_contract(),
        root=tmp_path,
        provider_factories={
            "twse_openapi_daily_material": lambda: twse,
            "tpex_openapi_daily_material": lambda: tpex,
        },
    )


def test_forward_runner_persists_raw_versions_and_hashed_manifest(tmp_path: Path) -> None:
    twse = FakeProvider(
        endpoint="https://example.test/twse", batch=_batch("twse", "2330", "上市重大訊息")
    )
    tpex = FakeProvider(
        endpoint="https://example.test/tpex", batch=_batch("tpex", "6488", "上櫃重大訊息")
    )
    observed_at = datetime(2026, 8, 30, 9, tzinfo=UTC)

    manifest = _runner(tmp_path, twse, tpex).run(
        phase="current", observed_at=observed_at
    )

    assert manifest["status"] == "SUCCESS"
    assert manifest["successful_source_count"] == 2
    assert manifest["automatic_retraining"] is False
    assert manifest["scheduler_deployed"] is False
    assert all(row["backoff_seconds"] == [1.0, 2.0] for row in manifest["sources"])
    assert len(list((tmp_path / "raw").rglob("*.bin"))) == 2
    assert len(list((tmp_path / "normalized").rglob("*.json"))) == 2
    manifest_files = list((tmp_path / "manifests").rglob("*.json"))
    assert len(manifest_files) == 1
    assert json.loads(manifest_files[0].read_text())["manifest_sha256"] == manifest[
        "manifest_sha256"
    ]
    assert not (tmp_path / ".collector.lock").exists()


def test_same_run_id_is_idempotent_without_second_provider_request(tmp_path: Path) -> None:
    twse = FakeProvider(
        endpoint="https://example.test/twse", batch=_batch("twse", "2330", "上市重大訊息")
    )
    tpex = FakeProvider(
        endpoint="https://example.test/tpex", batch=_batch("tpex", "6488", "上櫃重大訊息")
    )
    runner = _runner(tmp_path, twse, tpex)
    observed_at = datetime(2026, 8, 30, 9, tzinfo=UTC)

    first = runner.run(phase="evening", observed_at=observed_at)
    retry = runner.run(phase="evening", observed_at=observed_at)

    assert first == retry
    assert twse.calls == 1
    assert tpex.calls == 1
    assert len(list((tmp_path / "normalized").rglob("*.json"))) == 2


def test_partial_source_failure_is_manifested_and_never_claims_success(tmp_path: Path) -> None:
    twse = FakeProvider(
        endpoint="https://example.test/twse",
        batch=_batch("twse", "2330", "invalid schema payload"),
        parse_error=ValueError("synthetic schema drift"),
    )
    tpex = FakeProvider(
        endpoint="https://example.test/tpex", batch=_batch("tpex", "6488", "上櫃重大訊息")
    )

    with pytest.raises(ForwardCollectionRunError) as raised:
        _runner(tmp_path, twse, tpex).run(
            phase="next_morning",
            observed_at=datetime(2026, 8, 30, 23, tzinfo=UTC),
        )

    manifest = raised.value.manifest
    assert manifest["status"] == "PARTIAL_OR_FAILED"
    assert manifest["successful_source_count"] == 1
    failed = next(row for row in manifest["sources"] if row["status"] == "FAILED")
    assert failed == {
        "source_id": "twse_openapi_daily_material",
        "status": "FAILED",
        "error_type": "ValueError",
    }
    serialized = json.dumps(manifest)
    assert "synthetic schema drift" not in serialized
    assert len(list((tmp_path / "raw/twse_openapi_daily_material").rglob("*.bin"))) == 1


def test_concurrent_run_lock_fails_closed(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".collector.lock").write_text("occupied")
    runner = _runner(
        tmp_path,
        FakeProvider(endpoint="https://example.test/twse", batch=_batch("twse", "2330", "A")),
        FakeProvider(endpoint="https://example.test/tpex", batch=_batch("tpex", "6488", "B")),
    )

    with pytest.raises(ForwardCollectionLockedError):
        runner.run(
            phase="current",
            observed_at=datetime(2026, 8, 30, 9, tzinfo=UTC),
        )


def test_runner_rejects_naive_time_and_unknown_phase(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        FakeProvider(endpoint="https://example.test/twse", batch=_batch("twse", "2330", "A")),
        FakeProvider(endpoint="https://example.test/tpex", batch=_batch("tpex", "6488", "B")),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        runner.run(phase="current", observed_at=datetime(2026, 8, 30, 9))
    with pytest.raises(ValueError, match="unsupported reconciliation phase"):
        runner.run(
            phase="unknown",
            observed_at=datetime(2026, 8, 30, 9, tzinfo=UTC),
        )
