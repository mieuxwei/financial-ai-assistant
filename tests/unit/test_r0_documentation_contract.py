from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_documents_share_the_current_execution_boundary() -> None:
    handoff = _read("HANDOFF.md")
    plan = _read("PROJECT_PLAN.md")
    readme = _read("README.md")

    assert (
        "NEXT EXECUTABLE UNIT: **F11B-2 prerequisite remediation — do not begin integration**"
        in handoff
    )
    assert "F11B-2 prerequisite gate audit complete" in plan
    assert "F11B-2 prerequisite audit complete" in readme
    assert "2/9" in plan and "blocked" in plan.casefold()
    assert "2/9" in readme and "blocked" in readme.casefold()
    assert "B3.1" in handoff
    assert "B3.1" in plan
    assert "B3.1" in readme
    assert "AUTOMATED_SIGNAL_ONLY" in handoff
    assert "AUTOMATED_SIGNAL_ONLY" in plan
    assert "AUTOMATED_SIGNAL_ONLY" in readme
    assert "NEXT EXECUTABLE UNIT: **F12" not in handoff


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
