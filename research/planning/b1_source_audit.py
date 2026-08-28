from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

MANIFEST_VERSION = "b1-source-candidate-manifest-v1"
DEFAULT_MANIFEST = Path("research/configs/b1_source_candidate_manifest.v1.json")

SourceType = Literal[
    "OFFICIAL_ANNOUNCEMENT",
    "MEDIA_NEWS",
    "DOMAIN_CORPUS",
    "LICENSED_OPTIONAL",
    "OTHER",
]
Decision = Literal[
    "ACCEPT_PRIMARY",
    "ACCEPT_SECONDARY",
    "CONDITIONAL",
    "OPTIONAL_FUTURE",
    "HOLD",
    "REJECT",
]


class SourceCandidate(BaseModel):
    """Frozen B1 decision record; it is not an executable downloader."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    provider: str = Field(min_length=1)
    source_type: SourceType
    language: list[str] = Field(min_length=1)
    taiwan_domain_relevance: str = Field(min_length=1)
    company_ticker_mapping: str = Field(min_length=1)
    title_available: str = Field(min_length=1)
    body_text_available: str = Field(min_length=1)
    timestamp_available: str = Field(min_length=1)
    timestamp_timezone: str = Field(min_length=1)
    timestamp_semantics: str = Field(min_length=1)
    historical_coverage: str = Field(min_length=1)
    access_method: str = Field(min_length=1)
    api_stability: str = Field(min_length=1)
    duplicate_risk: str = Field(min_length=1)
    revision_risk: str = Field(min_length=1)
    licensing_status: str = Field(min_length=1)
    storage_allowed: str = Field(min_length=1)
    redistribution_allowed: str = Field(min_length=1)
    public_demo_text_allowed: str = Field(min_length=1)
    known_missingness: str = Field(min_length=1)
    known_delay: str = Field(min_length=1)
    reproducibility: str = Field(min_length=1)
    implementation_complexity: str = Field(min_length=1)
    research_value: str = Field(min_length=1)
    status: Decision
    approved_purposes: list[str] = Field(min_length=1)
    prohibited_uses: list[str] = Field(min_length=1)
    evidence_urls: list[HttpUrl] = Field(default_factory=list)
    evidence_files: list[str] = Field(default_factory=list)
    evidence_basis: Literal["repository_audit", "official_documentation", "both"]
    network_probe_performed_in_b1: bool = False

    @model_validator(mode="after")
    def require_evidence_reference(self) -> SourceCandidate:
        if not self.evidence_urls and not self.evidence_files:
            raise ValueError("at least one evidence URL or repository file is required")
        return self


class SourceStack(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class B1SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    manifest_version: Literal["b1-source-candidate-manifest-v1"] = MANIFEST_VERSION
    decision_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    scope: Literal["B1_SOURCE_CANDIDATE_AUDIT"] = "B1_SOURCE_CANDIDATE_AUDIT"
    sources: list[SourceCandidate] = Field(min_length=1)
    b2_whitelist: list[str] = Field(min_length=1)
    preferred_b2_stack: SourceStack
    fallback_b2_stack: SourceStack
    global_rules: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_decisions(self) -> B1SourceManifest:
        by_id = {source.source_id: source for source in self.sources}
        if len(by_id) != len(self.sources):
            raise ValueError("source_id values must be unique")

        accepted = {
            source.source_id
            for source in self.sources
            if source.status in {"ACCEPT_PRIMARY", "ACCEPT_SECONDARY"}
        }
        if set(self.b2_whitelist) != accepted:
            raise ValueError("b2_whitelist must equal all primary and secondary accepted sources")
        if len(set(self.b2_whitelist)) != len(self.b2_whitelist):
            raise ValueError("b2_whitelist values must be unique")

        for stack in (self.preferred_b2_stack, self.fallback_b2_stack):
            missing = set(stack.source_ids) - accepted
            if missing:
                raise ValueError(f"stack contains non-whitelisted sources: {sorted(missing)}")
            if len(set(stack.source_ids)) != len(stack.source_ids):
                raise ValueError("stack source_ids must be unique")

        eland = by_id.get("eland")
        if eland is None or eland.status != "HOLD":
            raise ValueError("eLAND must remain present as a HOLD / permanent exclusion record")
        if any("active" in purpose.casefold() for purpose in eland.approved_purposes):
            raise ValueError("eLAND cannot have an active approved purpose")

        ap11 = by_id.get("tej_ap11")
        if ap11 is None or ap11.status != "OPTIONAL_FUTURE":
            raise ValueError("TEJ/AP11 must remain optional unless a later audit supersedes B1")

        gdelt = by_id.get("gdelt_gkg_gal")
        if gdelt is None or "MEDIA_TONE_PROXY" not in gdelt.approved_purposes:
            raise ValueError("GDELT Tone must be constrained to MEDIA_TONE_PROXY")
        if not any("validated" in item.casefold() for item in gdelt.prohibited_uses):
            raise ValueError("GDELT must explicitly prohibit validated-sentiment claims")
        return self


def load_b1_manifest(path: Path = DEFAULT_MANIFEST) -> B1SourceManifest:
    return B1SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))


def decision_counts(manifest: B1SourceManifest) -> dict[str, int]:
    counts = {status: 0 for status in Decision.__args__}
    for source in manifest.sources:
        counts[source.status] += 1
    return counts
