from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pipelines.news.types import NewsItem
from research.planning.b1_source_audit import load_b1_manifest
from research.training.fsc_corpus import normalize_text

CONTRACT_VERSION = "b2-taiwan-financial-text-v1"
SCHEMA_VERSION = "b2-financial-document-v1"
DATASET_VERSION = "b2-taiwan-financial-text-dataset-v1"
DEFAULT_CONFIG = Path("research/configs/b2_taiwan_financial_text.v1.json")
DEFAULT_OUTPUT = Path(".tools/datasets/b2-taiwan-financial-text-v1")

SourceType = Literal["DOMAIN_CORPUS", "OFFICIAL_ANNOUNCEMENT", "MEDIA_NEWS"]
TimestampPrecision = Literal["date", "second"]


class SourceCollectionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str
    source_type: SourceType
    role: str = Field(min_length=1)
    collection_method: str = Field(min_length=1)
    recurring: bool
    schedule: list[str]
    collection_timezone: Literal["Asia/Taipei"]
    timeout_seconds: int = Field(ge=1, le=120)
    max_attempts: int = Field(ge=1, le=5)
    backoff_seconds: list[float]
    late_arrival_reconciliation: str = Field(min_length=1)
    raw_storage: str = Field(min_length=1)
    normalized_storage: str = Field(min_length=1)
    deduplication_strategy: str = Field(min_length=1)
    document_identity: str = Field(min_length=1)
    source_lineage: str = Field(min_length=1)
    retention_policy: str = Field(min_length=1)
    licensing_restrictions: str = Field(min_length=1)
    public_private_boundary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_schedule_and_retry(self) -> SourceCollectionContract:
        if self.recurring != bool(self.schedule):
            raise ValueError("recurring sources require a schedule and static sources forbid one")
        if len(self.backoff_seconds) != self.max_attempts - 1:
            raise ValueError("backoff_seconds must have max_attempts - 1 entries")
        if any(value <= 0 for value in self.backoff_seconds):
            raise ValueError("backoff values must be positive")
        return self


class DeploymentOption(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    not_deployed_in_b2: Literal[True] = True


class ModelRefreshPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    automatic_retraining: Literal[False] = False
    minimum_steps: list[str] = Field(min_length=5)


class B2Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: Literal["b2-taiwan-financial-text-v1"] = CONTRACT_VERSION
    schema_version: Literal["b2-financial-document-v1"] = SCHEMA_VERSION
    timezone: Literal["Asia/Taipei"] = "Asia/Taipei"
    snapshot_ingestion_timestamp: datetime
    no_minimum_forward_collection_wait: Literal[True] = True
    b1_manifest_path: Path
    fsc_corpus_dir: Path
    local_dataset_dir: Path
    sources: list[SourceCollectionContract] = Field(min_length=1)
    recommended_deployment: DeploymentOption
    fallback_deployment: DeploymentOption
    model_refresh_policy: ModelRefreshPolicy

    @model_validator(mode="after")
    def validate_whitelist_and_source_roles(self) -> B2Contract:
        if self.snapshot_ingestion_timestamp.tzinfo is None:
            raise ValueError("snapshot_ingestion_timestamp must be timezone-aware")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("B2 source IDs must be unique")
        whitelist = load_b1_manifest(self.b1_manifest_path).b2_whitelist
        if source_ids != whitelist:
            raise ValueError("B2 sources must exactly preserve B1 whitelist order")
        by_id = {source.source_id: source for source in self.sources}
        if by_id["fsc_filtered_corpus"].recurring:
            raise ValueError("FSC is static and cannot have recurring collection")
        if by_id["gdelt_gkg_gal"].source_type != "MEDIA_NEWS":
            raise ValueError("GDELT must remain MEDIA_NEWS")
        for source_id in ("twse_openapi_daily_material", "tpex_openapi_daily_material"):
            if by_id[source_id].source_type != "OFFICIAL_ANNOUNCEMENT":
                raise ValueError("TWSE/TPEx must remain OFFICIAL_ANNOUNCEMENT")
        return self


class TickerMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticker: str = Field(min_length=1, max_length=20)
    company: str | None = None
    method: Literal[
        "official_company_code",
        "company_alias_title",
        "company_alias_metadata",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class B2Document(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["b2-financial-document-v1"] = SCHEMA_VERSION
    document_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    document_version_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_id: str
    source_type: SourceType
    provider: str
    external_id: str
    publication_timestamp: datetime
    timezone: str
    timestamp_semantics: str
    timestamp_precision: TimestampPrecision
    ingestion_timestamp: datetime
    language: str
    title: str | None = None
    permitted_text: str | None = None
    source_url: str | None = None
    event_category: str | None = None
    ticker_mappings: list[TickerMapping] = Field(default_factory=list)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_payload_ref: str
    lineage: dict[str, str]
    rights_tier: Literal[
        "PRIVATE_DOMAIN_CORPUS",
        "OFFICIAL_OPEN_DATA_PRIVATE_TEXT",
        "MEDIA_METADATA_ONLY",
    ]
    public_demo_text_allowed: bool
    media_tone_proxy: float | None = None

    @field_validator("publication_timestamp", "ingestion_timestamp")
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_source_semantics(self) -> B2Document:
        if self.source_type == "MEDIA_NEWS" and self.rights_tier != "MEDIA_METADATA_ONLY":
            raise ValueError("media sources are metadata-only under B2")
        if self.source_type == "MEDIA_NEWS" and self.permitted_text is not None:
            raise ValueError("publisher article text is forbidden in B2 media records")
        if self.source_type != "MEDIA_NEWS" and self.media_tone_proxy is not None:
            raise ValueError("media tone proxy is only valid for MEDIA_NEWS")
        if self.source_id == "fsc_filtered_corpus" and self.ticker_mappings:
            raise ValueError("FSC domain corpus cannot invent ticker mappings")
        return self


@dataclass(frozen=True)
class CollectionResult:
    raw_snapshot_created: bool
    inserted_versions: int
    duplicate_versions: int
    raw_sha256: str


def load_b2_contract(path: Path = DEFAULT_CONFIG) -> B2Contract:
    return B2Contract.model_validate_json(path.read_text(encoding="utf-8"))


def build_fsc_b2_snapshot(
    contract: B2Contract,
    *,
    output_dir: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = generated_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    target_dir = output_dir or contract.local_dataset_dir
    source_manifest_path = contract.fsc_corpus_dir / "manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("retained_record_count") != 6021:
        raise ValueError("approved FSC corpus must contain exactly 6,021 records")

    split_reports: dict[str, dict[str, object]] = {}
    semantic_hash = hashlib.sha256()
    document_ids: set[str] = set()
    version_ids: set[str] = set()
    for split in ("train", "validation", "test"):
        rows = _read_jsonl(contract.fsc_corpus_dir / f"{split}.jsonl")
        documents = [
            _normalize_fsc(row, split, contract.snapshot_ingestion_timestamp) for row in rows
        ]
        for document in documents:
            if document.document_id in document_ids or document.document_version_id in version_ids:
                raise ValueError("duplicate document identity in FSC B2 snapshot")
            document_ids.add(document.document_id)
            version_ids.add(document.document_version_id)
        payload = _jsonl_bytes(documents)
        semantic_hash.update(payload)
        _write_immutable(target_dir / f"{split}.jsonl", payload)
        split_reports[split] = {
            "record_count": len(documents),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "min_publication_timestamp": min(
                (item.publication_timestamp.isoformat() for item in documents), default=None
            ),
            "max_publication_timestamp": max(
                (item.publication_timestamp.isoformat() for item in documents), default=None
            ),
        }

    report = {
        "dataset_version": DATASET_VERSION,
        "contract_version": contract.contract_version,
        "schema_version": contract.schema_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "source_manifest_version": source_manifest["corpus_version"],
        "source_corpus_sha256": source_manifest["corpus_sha256"],
        "record_count": len(document_ids),
        "source_counts": {"fsc_filtered_corpus": len(document_ids)},
        "source_types": {"DOMAIN_CORPUS": len(document_ids)},
        "split_files": split_reports,
        "dataset_sha256": semantic_hash.hexdigest(),
        "raw_text_committed": False,
        "manual_labels_used": False,
        "sentiment_ground_truth": False,
        "forward_source_baseline_counts": {
            "twse_openapi_daily_material": 0,
            "tpex_openapi_daily_material": 0,
            "gdelt_gkg_gal": 0,
        },
        "no_minimum_forward_collection_wait": True,
    }
    immutable_report = {key: value for key, value in report.items() if key != "generated_at"}
    _write_immutable(
        target_dir / "manifest.json",
        (
            json.dumps(immutable_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode(),
    )
    return report


def persist_collection_batch(
    *,
    source_id: str,
    raw_content_kind: Literal["OFFICIAL_OPEN_DATA", "GDELT_METADATA_ONLY"],
    raw_payload: bytes,
    documents: list[B2Document],
    root: Path,
    observed_at: datetime,
) -> CollectionResult:
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    expected_kind = (
        "GDELT_METADATA_ONLY"
        if source_id == "gdelt_gkg_gal"
        else "OFFICIAL_OPEN_DATA"
    )
    if raw_content_kind != expected_kind:
        raise ValueError("raw content kind violates the source rights contract")
    raw_sha256 = hashlib.sha256(raw_payload).hexdigest()
    date_path = observed_at.astimezone(UTC).strftime("%Y/%m/%d")
    raw_path = root / "raw" / source_id / date_path / f"{raw_sha256}.bin"
    raw_created = _write_immutable(raw_path, raw_payload)
    inserted = 0
    duplicates = 0
    for document in documents:
        if document.source_id != source_id:
            raise ValueError("document source does not match collection batch")
        payload = _json_line(document)
        target = root / "normalized" / source_id / f"{document.document_version_id}.json"
        if _write_immutable(target, payload):
            inserted += 1
        else:
            duplicates += 1
    return CollectionResult(raw_created, inserted, duplicates, raw_sha256)


def stable_document_id(source_id: str, external_identity: str) -> str:
    return _sha256(f"{source_id}\x1f{external_identity}")


def stable_version_id(document_id: str, content_digest: str) -> str:
    return _sha256(f"{document_id}\x1f{content_digest}")


def normalize_news_item(
    *,
    source_id: str,
    source_type: Literal["OFFICIAL_ANNOUNCEMENT", "MEDIA_NEWS"],
    provider: str,
    item: NewsItem,
    raw_payload_ref: str,
    ingestion_timestamp: datetime,
    ticker_mappings: list[TickerMapping] | None = None,
) -> B2Document:
    if ingestion_timestamp.tzinfo is None:
        raise ValueError("ingestion_timestamp must be timezone-aware")
    external_identity = item.external_id or item.url
    document_id = stable_document_id(source_id, external_identity)
    title = normalize_text(item.title)
    mappings = ticker_mappings or [
        TickerMapping(
            ticker=ticker,
            company=str(item.metadata.get("company_name") or "") or None,
            method="official_company_code",
            confidence=1.0,
        )
        for ticker in item.explicit_tickers
    ]
    permitted_text = normalize_text(item.summary) if item.summary else None
    if source_type == "MEDIA_NEWS":
        permitted_text = None
    content_basis = json.dumps(
        {
            "title": title,
            "permitted_text": permitted_text,
            "event_category": item.metadata.get("clause"),
            "source_url": item.url,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    content_digest = _sha256(content_basis)
    tone = item.metadata.get("media_tone_proxy")
    return B2Document(
        document_id=document_id,
        document_version_id=stable_version_id(document_id, content_digest),
        source_id=source_id,
        source_type=source_type,
        provider=provider,
        external_id=external_identity,
        publication_timestamp=item.published_at,
        timezone=str(item.published_at.tzinfo),
        timestamp_semantics=(
            "official announcement publication time"
            if source_type == "OFFICIAL_ANNOUNCEMENT"
            else "GDELT source-document publication time; batch time remains separate"
        ),
        timestamp_precision="second",
        ingestion_timestamp=ingestion_timestamp,
        language=item.language,
        title=title,
        permitted_text=permitted_text,
        source_url=item.url,
        event_category=str(item.metadata.get("clause") or "") or None,
        ticker_mappings=mappings,
        content_hash=content_digest,
        raw_payload_ref=raw_payload_ref,
        lineage={
            "provider_external_id": external_identity,
            "pipeline_version": CONTRACT_VERSION,
        },
        rights_tier=(
            "OFFICIAL_OPEN_DATA_PRIVATE_TEXT"
            if source_type == "OFFICIAL_ANNOUNCEMENT"
            else "MEDIA_METADATA_ONLY"
        ),
        public_demo_text_allowed=False,
        media_tone_proxy=float(tone) if tone is not None else None,
    )


def _normalize_fsc(row: dict[str, object], split: str, observed_at: datetime) -> B2Document:
    text = normalize_text(str(row["text"]))
    external_id = str(row["record_id"])
    document_id = stable_document_id("fsc_filtered_corpus", external_id)
    content_digest = _sha256(text)
    publication_date = str(row["publication_date"])
    publication_timestamp = datetime.fromisoformat(f"{publication_date}T00:00:00+08:00")
    return B2Document(
        document_id=document_id,
        document_version_id=stable_version_id(document_id, content_digest),
        source_id="fsc_filtered_corpus",
        source_type="DOMAIN_CORPUS",
        provider=f"FSC/{row['agency']}",
        external_id=external_id,
        publication_timestamp=publication_timestamp,
        timezone="Asia/Taipei",
        timestamp_semantics="official archive publication date; date precision only",
        timestamp_precision="date",
        ingestion_timestamp=observed_at,
        language="zh-TW",
        title=None,
        permitted_text=text,
        source_url=None,
        event_category=None,
        ticker_mappings=[],
        content_hash=content_digest,
        raw_payload_ref=f"fsc-domain-corpus-v1/{split}.jsonl#{external_id}",
        lineage={
            "source_record_id": external_id,
            "source_content_sha256": str(row["content_sha256"]),
            "family_sha256": str(row["family_sha256"]),
            "split": split,
            "pipeline_version": CONTRACT_VERSION,
        },
        rights_tier="PRIVATE_DOMAIN_CORPUS",
        public_demo_text_allowed=False,
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _json_line(document: B2Document) -> bytes:
    return (
        json.dumps(
            document.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def _jsonl_bytes(documents: list[B2Document]) -> bytes:
    return b"".join(_json_line(document) for document in documents)


def _write_immutable(path: Path, payload: bytes) -> bool:
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite different immutable data: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
