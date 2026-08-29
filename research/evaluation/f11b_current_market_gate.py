from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GATE_IDS = (
    "current_ohlcv_source_audited",
    "taiex_source_audited",
    "exact_23_feature_parity_verified",
    "cutoff_semantics_verified",
    "timezone_verified",
    "missing_data_rules_frozen",
    "training_inference_feature_parity_verified",
    "lineage_available",
    "validation_passed",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GateResult(StrictModel):
    id: str
    status: Literal["PASS", "BLOCKED"]
    reason: str = Field(min_length=20)


class GateSummary(StrictModel):
    required: Literal[9]
    passed: int = Field(ge=0, le=9)
    blocked: int = Field(ge=0, le=9)
    all_passed: bool


class CurrentMarketGateAudit(StrictModel):
    schema_version: Literal["f11b-current-market-gate-audit-v1"]
    milestone: Literal["F11B-2_PREREQUISITE_GATE_AUDIT"]
    audit_date: str
    probe_window: dict[str, object]
    stock_source: dict[str, object]
    benchmark_source: dict[str, object]
    adjusted_ohlcv_alternative_probe: dict[str, object]
    observed_contract_conflicts: list[str] = Field(min_length=1)
    gates: list[GateResult] = Field(min_length=9, max_length=9)
    gate_summary: GateSummary
    f11b_2_integration_allowed: bool
    f11b_2_started: Literal[False]
    live_gas_modified: Literal[False]
    deployed: Literal[False]
    portfolio_mutated: Literal[False]
    next_executable_unit: Literal["F11B_2_PREREQUISITE_REMEDIATION"]

    @model_validator(mode="after")
    def validate_gate_contract(self) -> CurrentMarketGateAudit:
        if tuple(gate.id for gate in self.gates) != GATE_IDS:
            raise ValueError("F11B-2 gates must match the frozen order")
        passed = sum(gate.status == "PASS" for gate in self.gates)
        blocked = len(self.gates) - passed
        if (self.gate_summary.passed, self.gate_summary.blocked) != (passed, blocked):
            raise ValueError("F11B-2 gate counts drifted")
        all_passed = blocked == 0
        if self.gate_summary.all_passed != all_passed:
            raise ValueError("F11B-2 all_passed summary drifted")
        if self.f11b_2_integration_allowed != all_passed:
            raise ValueError("F11B-2 integration cannot bypass a blocked gate")
        if self.stock_source.get("accepted_for_current_serving") is not False:
            raise ValueError("current OHLCV source decision drifted")
        if self.benchmark_source.get("accepted_for_current_serving") is not True:
            raise ValueError("TAIEX source decision drifted")
        alternative_entitled = self.adjusted_ohlcv_alternative_probe.get(
            "entitled_in_current_environment"
        )
        if alternative_entitled is not False:
            raise ValueError("adjusted OHLCV alternative entitlement drifted")
        return self

    @property
    def canonical_sha256(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def load_current_market_gate_audit(path: Path) -> CurrentMarketGateAudit:
    return CurrentMarketGateAudit.model_validate_json(path.read_text(encoding="utf-8"))
