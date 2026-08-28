import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.planning.b1_source_audit import (
    B1SourceManifest,
    decision_counts,
    load_b1_manifest,
)

MANIFEST_PATH = Path("research/configs/b1_source_candidate_manifest.v1.json")


def test_committed_b1_manifest_is_complete_and_frozen() -> None:
    manifest = load_b1_manifest(MANIFEST_PATH)

    assert len(manifest.sources) == 15
    assert decision_counts(manifest) == {
        "ACCEPT_PRIMARY": 2,
        "ACCEPT_SECONDARY": 2,
        "CONDITIONAL": 1,
        "OPTIONAL_FUTURE": 2,
        "HOLD": 8,
        "REJECT": 0,
    }
    assert manifest.b2_whitelist == [
        "fsc_filtered_corpus",
        "twse_openapi_daily_material",
        "tpex_openapi_daily_material",
        "gdelt_gkg_gal",
    ]


def test_every_candidate_has_required_audit_dimensions() -> None:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source_model = B1SourceManifest.model_fields["sources"].annotation.__args__[0]
    required = {name for name, field in source_model.model_fields.items() if field.is_required()}

    for source in raw["sources"]:
        assert required <= set(source)
        assert source["approved_purposes"]
        assert source["prohibited_uses"]
        assert source["evidence_urls"] or source["evidence_files"]
        assert source["network_probe_performed_in_b1"] is False


def test_official_and_media_semantics_cannot_be_silently_merged() -> None:
    manifest = load_b1_manifest(MANIFEST_PATH)
    by_id = {source.source_id: source for source in manifest.sources}

    assert by_id["twse_openapi_daily_material"].source_type == "OFFICIAL_ANNOUNCEMENT"
    assert by_id["tpex_openapi_daily_material"].source_type == "OFFICIAL_ANNOUNCEMENT"
    assert by_id["gdelt_gkg_gal"].source_type == "MEDIA_NEWS"
    assert "MEDIA_TONE_PROXY" in by_id["gdelt_gkg_gal"].approved_purposes
    assert "validated financial sentiment" in by_id["gdelt_gkg_gal"].prohibited_uses


def test_eland_and_unresolved_sources_are_not_whitelisted() -> None:
    manifest = load_b1_manifest(MANIFEST_PATH)
    by_id = {source.source_id: source for source in manifest.sources}

    assert by_id["eland"].status == "HOLD"
    assert by_id["tej_ap11"].status == "OPTIONAL_FUTURE"
    assert by_id["twmd_major_events"].status == "HOLD"
    assert by_id["finmind_taiwan_stock_news"].status == "CONDITIONAL"
    assert not {
        "eland",
        "tej_ap11",
        "twmd_major_events",
        "finmind_taiwan_stock_news",
    } & set(manifest.b2_whitelist)


def test_manifest_rejects_nonaccepted_whitelist_entries() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["b2_whitelist"].append("finmind_taiwan_stock_news")

    with pytest.raises(ValidationError, match="b2_whitelist"):
        B1SourceManifest.model_validate(payload)


def test_manifest_rejects_eland_reactivation() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    eland = next(source for source in payload["sources"] if source["source_id"] == "eland")
    eland["status"] = "REJECT"

    with pytest.raises(ValidationError, match="eLAND"):
        B1SourceManifest.model_validate(payload)
