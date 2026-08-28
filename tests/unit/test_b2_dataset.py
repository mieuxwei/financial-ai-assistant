import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipelines.news.b2_dataset import (
    B2Contract,
    B2Document,
    build_fsc_b2_snapshot,
    load_b2_contract,
    normalize_news_item,
    persist_collection_batch,
    stable_document_id,
    stable_version_id,
)
from pipelines.news.types import NewsItem


def _media_document(*, title_hash: str = "a" * 64) -> B2Document:
    document_id = stable_document_id("gdelt_gkg_gal", "https://example.test/article")
    return B2Document(
        document_id=document_id,
        document_version_id=stable_version_id(document_id, title_hash),
        source_id="gdelt_gkg_gal",
        source_type="MEDIA_NEWS",
        provider="GDELT",
        external_id="https://example.test/article",
        publication_timestamp="2026-08-29T01:00:00Z",
        timezone="UTC",
        timestamp_semantics="GKG source-document publication time",
        timestamp_precision="second",
        ingestion_timestamp="2026-08-29T02:00:00Z",
        language="zh-TW",
        title="synthetic metadata title",
        permitted_text=None,
        source_url="https://example.test/article",
        ticker_mappings=[],
        content_hash=title_hash,
        raw_payload_ref="raw/gdelt/synthetic",
        lineage={"partition": "synthetic", "pipeline_version": "test"},
        rights_tier="MEDIA_METADATA_ONLY",
        public_demo_text_allowed=False,
        media_tone_proxy=0.25,
    )


def test_b2_contract_exactly_preserves_b1_whitelist_and_roles() -> None:
    contract = load_b2_contract()

    assert [source.source_id for source in contract.sources] == [
        "fsc_filtered_corpus",
        "twse_openapi_daily_material",
        "tpex_openapi_daily_material",
        "gdelt_gkg_gal",
    ]
    assert contract.no_minimum_forward_collection_wait is True
    assert contract.sources[0].recurring is False
    assert all(source.recurring for source in contract.sources[1:])
    assert contract.model_refresh_policy.automatic_retraining is False
    assert contract.recommended_deployment.not_deployed_in_b2 is True


def test_contract_rejects_conditional_source_and_wait_requirement() -> None:
    payload = json.loads(
        Path("research/configs/b2_taiwan_financial_text.v1.json").read_text(encoding="utf-8")
    )
    payload["sources"][3]["source_id"] = "finmind_taiwan_stock_news"
    with pytest.raises(ValidationError, match="B1 whitelist"):
        B2Contract.model_validate(payload)

    payload = json.loads(
        Path("research/configs/b2_taiwan_financial_text.v1.json").read_text(encoding="utf-8")
    )
    payload["no_minimum_forward_collection_wait"] = False
    with pytest.raises(ValidationError):
        B2Contract.model_validate(payload)


def test_media_document_forbids_publisher_body_and_sentiment_truth_shape() -> None:
    payload = _media_document().model_dump(mode="json")
    payload["permitted_text"] = "publisher body must not be stored"
    with pytest.raises(ValidationError, match="publisher article text"):
        B2Document.model_validate(payload)

    payload = _media_document().model_dump(mode="json")
    payload["rights_tier"] = "PRIVATE_DOMAIN_CORPUS"
    with pytest.raises(ValidationError, match="metadata-only"):
        B2Document.model_validate(payload)


def test_collection_retries_are_idempotent_and_revisions_are_immutable(tmp_path: Path) -> None:
    observed_at = datetime(2026, 8, 29, 2, tzinfo=UTC)
    raw = b'{"synthetic":true}'
    first_doc = _media_document()
    first = persist_collection_batch(
        source_id="gdelt_gkg_gal",
        raw_content_kind="GDELT_METADATA_ONLY",
        raw_payload=raw,
        documents=[first_doc],
        root=tmp_path,
        observed_at=observed_at,
    )
    retry = persist_collection_batch(
        source_id="gdelt_gkg_gal",
        raw_content_kind="GDELT_METADATA_ONLY",
        raw_payload=raw,
        documents=[first_doc],
        root=tmp_path,
        observed_at=observed_at,
    )
    revised_doc = _media_document(title_hash="b" * 64)
    revision = persist_collection_batch(
        source_id="gdelt_gkg_gal",
        raw_content_kind="GDELT_METADATA_ONLY",
        raw_payload=b'{"synthetic":"revision"}',
        documents=[revised_doc],
        root=tmp_path,
        observed_at=observed_at,
    )

    assert (first.raw_snapshot_created, first.inserted_versions, first.duplicate_versions) == (
        True,
        1,
        0,
    )
    assert (retry.raw_snapshot_created, retry.inserted_versions, retry.duplicate_versions) == (
        False,
        0,
        1,
    )
    assert revision.inserted_versions == 1
    assert first_doc.document_id == revised_doc.document_id
    assert first_doc.document_version_id != revised_doc.document_version_id
    assert len(list((tmp_path / "normalized/gdelt_gkg_gal").glob("*.json"))) == 2


def test_collection_rejects_cross_source_rows(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source does not match"):
        persist_collection_batch(
            source_id="twse_openapi_daily_material",
            raw_content_kind="OFFICIAL_OPEN_DATA",
            raw_payload=b"[]",
            documents=[_media_document()],
            root=tmp_path,
            observed_at=datetime.now(UTC),
        )


def test_collection_rejects_media_payload_misclassified_as_official_data(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="rights contract"):
        persist_collection_batch(
            source_id="gdelt_gkg_gal",
            raw_content_kind="OFFICIAL_OPEN_DATA",
            raw_payload=b'{"not":"approved-as-open-data"}',
            documents=[_media_document()],
            root=tmp_path,
            observed_at=datetime.now(UTC),
        )


def test_official_and_media_normalization_keep_rights_and_time_semantics_separate() -> None:
    official_item = NewsItem(
        title="官方重大訊息",
        summary="官方公開說明",
        published_at=datetime.fromisoformat("2026-08-29T17:45:01+08:00"),
        source="twse_material",
        source_type="official_announcement",
        url="https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
        external_id="official-1",
        explicit_tickers=("2330",),
        metadata={"company_name": "台積電", "clause": "第14款"},
    )
    official = normalize_news_item(
        source_id="twse_openapi_daily_material",
        source_type="OFFICIAL_ANNOUNCEMENT",
        provider="TWSE",
        item=official_item,
        raw_payload_ref="raw/twse/synthetic",
        ingestion_timestamp=datetime(2026, 8, 29, 10, tzinfo=UTC),
    )
    media_item = NewsItem(
        title="媒體標題",
        summary="這段模擬 publisher body 必須被丟棄",
        published_at=datetime(2026, 8, 29, 1, tzinfo=UTC),
        source="gdelt",
        source_type="media_news",
        url="https://example.test/media",
        external_id="media-1",
        metadata={"media_tone_proxy": -1.5},
    )
    media = normalize_news_item(
        source_id="gdelt_gkg_gal",
        source_type="MEDIA_NEWS",
        provider="GDELT",
        item=media_item,
        raw_payload_ref="raw/gdelt/synthetic",
        ingestion_timestamp=datetime(2026, 8, 29, 2, tzinfo=UTC),
    )

    assert official.permitted_text == "官方公開說明"
    assert official.ticker_mappings[0].method == "official_company_code"
    assert official.timestamp_semantics == "official announcement publication time"
    assert media.permitted_text is None
    assert media.media_tone_proxy == -1.5
    assert "GDELT" in media.timestamp_semantics


def test_fsc_snapshot_build_is_reproducible_and_raw_free_in_report(tmp_path: Path) -> None:
    contract = load_b2_contract()
    report = build_fsc_b2_snapshot(
        contract,
        output_dir=tmp_path / "b2",
        generated_at=datetime(2026, 8, 29, tzinfo=UTC),
    )
    second = build_fsc_b2_snapshot(
        contract,
        output_dir=tmp_path / "b2",
        generated_at=datetime(2026, 8, 30, tzinfo=UTC),
    )

    assert report["record_count"] == 6021
    assert report["source_counts"] == {"fsc_filtered_corpus": 6021}
    assert report["dataset_sha256"] == second["dataset_sha256"]
    assert report["raw_text_committed"] is False
    assert report["manual_labels_used"] is False
    assert report["sentiment_ground_truth"] is False
    assert report["no_minimum_forward_collection_wait"] is True
    assert hashlib.sha256((tmp_path / "b2/manifest.json").read_bytes()).hexdigest()
