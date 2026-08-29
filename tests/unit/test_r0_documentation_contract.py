from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_documents_share_the_current_execution_boundary() -> None:
    handoff = _read("HANDOFF.md")
    plan = _read("PROJECT_PLAN.md")
    readme = _read("README.md")

    assert "NEXT EXECUTABLE UNIT: **B4 — Validation / Abstention Decision only**" in handoff
    assert "next executable unit is B4 Validation / Abstention Decision only" in plan
    assert "next: B4 only" in readme
    assert "NEXT EXECUTABLE UNIT: **F12" not in handoff


def test_core_documents_freeze_track_a_and_split_f11() -> None:
    for document in (_read("HANDOFF.md"), _read("PROJECT_PLAN.md"), _read("README.md")):
        assert "F11A" in document
        assert "F11B" in document
        assert "Ridge" in document
        assert "alpha 100" in document or "alpha=100" in document


def test_source_and_gas_boundaries_are_explicit() -> None:
    handoff = _read("HANDOFF.md")
    protocol = _read("docs/r0_project_rebaseline_protocol.md")
    gas_freeze = _read("docs/gas_migration_safety_freeze.md")

    assert "AP11: **optional enhancement" in handoff
    assert "eLAND: **permanent historical exclusion" in handoff
    assert "Zero manual annotation" in protocol
    assert "live behavior unchanged" in gas_freeze
    assert "migration-copy" in gas_freeze
