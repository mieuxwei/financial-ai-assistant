from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_and_archived_documents_preserve_final_research_boundaries() -> None:
    assert not (ROOT / "HANDOFF.md").exists()
    assert not (ROOT / "PROJECT_PLAN.md").exists()
    handoff = _read("docs/internal/development_history.md")
    plan = _read("docs/internal/project_plan_archive.md")
    readme = _read("README.md")

    assert "Development History Archive" in handoff
    assert "Historical Project Plan Archive" in plan
    assert "R1B-UX1 LIFF Multi-Holding Form" in handoff
    assert "PROTOTYPE-COMPLETE / NOT PRIMARY PORTFOLIO ENTRY" in handoff
    assert "FORWARD_COLLECTION_DEPLOYED_AND_SMOKE_VERIFIED" in plan
    assert "AUDIT_COMPLETE_IMPLEMENTATION_NOT_READY" in handoff
    assert "AUDIT_COMPLETE_IMPLEMENTATION_NOT_READY" in plan
    assert "DEPLOYED / FIRST_BOUNDED_LIVE_SMOKE_VERIFIED" in handoff
    assert "FORWARD_COLLECTION_DEPLOYED_AND_SMOKE_VERIFIED" in handoff
    assert "reused_remote_manifest=true" in plan
    assert "Streamlit is the primary entry" in readme
    assert "PUBLIC_WEB_DEMO_DEPLOYED" in plan
    assert "LINE_PUBLIC_BETA_DEPLOYED" in plan
    assert "mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app" in readme
    assert "Experimental messaging:" in readme
    assert all(item in plan for item in ("F11B-2A", "F12", "R1A", "R1B-UX1"))
    assert "6/9" in plan and "blocked" in plan.casefold()
    assert "6/9" in readme and "disabled" in readme.casefold()
    assert "B3.1" in handoff
    assert "B3.1" in plan
    assert "中文情緒仍未通過獨立驗證" in readme
    assert "AUTOMATED_SIGNAL_ONLY" in handoff
    assert "AUTOMATED_SIGNAL_ONLY" in plan
    assert "automated historical-association signal" in readme.casefold()
    assert "NOT_READY_FOR_F11B_2" in handoff
    assert "Open Live Demo" in readme
    assert "modest" in readme.casefold() and "ranking signal" in readme.casefold()


def test_f11b_1b_documentation_preserves_controlled_demo_boundary() -> None:
    document = _read("docs/f11b_controlled_line_demo.md")
    gate_audit = _read("research/evaluation/f11b_current_market_gate_audit.md")

    assert "CONTROLLED RESEARCH DEMO" in document
    assert "NOT DEPLOYED" in document
    assert "fixture_only = true" in document
    assert "external_api_called = false" in document
    assert "model_inference_performed = false" in document
    assert "portfolio_write = false" in document
    assert "raw-body/header" in document
    assert "two of nine current-market gates" in document
    assert "2 PASS, 7 BLOCKED" in gate_audit
    assert "F11B-2 cannot start" in gate_audit


def test_core_documents_freeze_track_a_and_split_f11() -> None:
    for document in (
        _read("docs/internal/development_history.md"),
        _read("docs/internal/project_plan_archive.md"),
    ):
        assert "F11A" in document
        assert "F11B" in document
        assert "Ridge" in document
        assert "alpha 100" in document or "alpha=100" in document

    readme = _read("README.md")
    assert "Streamlit" in readme
    assert "LINE/GAS" in readme
    assert "Ridge" in readme
    assert "alpha = 100" in readme


def test_source_and_gas_boundaries_are_explicit() -> None:
    handoff = _read("docs/internal/development_history.md")
    protocol = _read("docs/internal/r0_project_rebaseline_protocol.md")
    gas_freeze = _read("docs/internal/gas_migration_safety_freeze.md")

    assert "AP11: **optional enhancement" in handoff
    assert "eLAND: **permanent historical exclusion" in handoff
    assert "Zero manual annotation" in protocol
    assert "live behavior unchanged" in gas_freeze
    assert "migration-copy" in gas_freeze
