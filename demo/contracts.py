from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.research import (
    FinancialIntelligenceItem,
    VolatilitySurprisePredictionRequest,
    VolatilitySurprisePredictionResponse,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DashboardDemoConfig(StrictModel):
    schema_version: Literal["dashboard-demo-config-v1"]
    dashboard_version: Literal["financial-ai-dashboard-v1"]
    streamlit_version_constraint: Literal[">=1.62,<2.0"]
    app_title: str
    modes: tuple[Literal["CONTROLLED_OFFLINE", "LOCAL_API"], ...]
    default_mode: Literal["CONTROLLED_OFFLINE"]
    fixture_path: Literal["demo/fixtures/controlled_dashboard_demo.v1.json"]
    local_api_default_base_url: Literal["http://127.0.0.1:8000"]
    allowed_api_hosts: tuple[Literal["127.0.0.1", "localhost", "::1"], ...]
    maximum_intelligence_items: int = Field(ge=1, le=50)
    controlled_data_only: Literal[True]
    private_holdings_in_demo: Literal[False]
    external_api_calls_in_offline_mode: Literal[False]
    automatic_gas_modification: Literal[False]
    deploy_in_f11: Literal[False]

    @model_validator(mode="after")
    def validate_demo_boundary(self) -> DashboardDemoConfig:
        if self.modes != ("CONTROLLED_OFFLINE", "LOCAL_API"):
            raise ValueError("F11 dashboard modes drifted")
        if set(self.allowed_api_hosts) != {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("F11 allowed API hosts drifted")
        if self.maximum_intelligence_items != 10:
            raise ValueError("F11 intelligence limit drifted")
        return self


class FeatureContext(StrictModel):
    return_20_session_pct: float
    volatility_20_session_pct: float
    volume_zscore_20: float
    benchmark_return_20_session_pct: float
    benchmark_drawdown_20_session_pct: float


class ControlledDashboardFixture(StrictModel):
    schema_version: Literal["controlled-dashboard-fixture-v1"]
    fixture_id: Literal["synthetic-2330-f11-v1"]
    controlled_synthetic_data: Literal[True]
    actual_market_observation: Literal[False]
    performance_evaluation: Literal[False]
    private_or_user_data: Literal[False]
    company_display_name: str
    data_notice: str
    feature_context: FeatureContext
    prediction_request: VolatilitySurprisePredictionRequest
    prediction_response: VolatilitySurprisePredictionResponse
    intelligence_version: str
    intelligence_items: list[FinancialIntelligenceItem]

    @model_validator(mode="after")
    def validate_cross_contract(self) -> ControlledDashboardFixture:
        ticker = self.prediction_request.ticker
        if self.prediction_response.ticker != ticker:
            raise ValueError("fixture prediction ticker mismatch")
        if any(
            ticker not in {match.ticker for match in item.ticker_matches}
            for item in self.intelligence_items
        ):
            raise ValueError("fixture intelligence ticker mismatch")
        if self.prediction_response.as_of_date != self.prediction_request.as_of_date:
            raise ValueError("fixture prediction date mismatch")
        if not self.prediction_response.claim_boundary.research_signal_only:
            raise ValueError("fixture must remain a research-only signal")
        if any(item.claim_boundary.llm_generated for item in self.intelligence_items):
            raise ValueError("fixture cannot contain LLM-generated intelligence")
        return self


def load_dashboard_config(path: Path) -> DashboardDemoConfig:
    return DashboardDemoConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_controlled_fixture(path: Path) -> ControlledDashboardFixture:
    return ControlledDashboardFixture.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_dashboard_config_sha256(config: DashboardDemoConfig) -> str:
    return _canonical_hash(config.model_dump(mode="json"))


def canonical_fixture_sha256(fixture: ControlledDashboardFixture) -> str:
    return _canonical_hash(fixture.model_dump(mode="json"))


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
