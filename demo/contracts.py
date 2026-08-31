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


class PublicWebDemoReleaseConfig(StrictModel):
    schema_version: Literal["public-web-demo-release-v1"]
    release_unit: Literal["R1A"]
    release_status: Literal["PUBLIC_WEB_DEMO_DEPLOYED"]
    hosting_provider: Literal["STREAMLIT_COMMUNITY_CLOUD"]
    deployment_topology: Literal["STREAMLIT_FIXTURE_ONLY"]
    entrypoint: Literal["demo/public_app.py"]
    python_version: Literal["3.12"]
    controlled_fixture_only: Literal[True]
    zero_runtime_secret: Literal[True]
    fastapi_required: Literal[False]
    request_time_network_calls: Literal[False]
    current_market_inference_enabled: Literal[False]
    chinese_sentiment_enabled: Literal[False]
    price_direction_enabled: Literal[False]
    portfolio_input_enabled: Literal[True]
    primary_public_experience: Literal["LIVE_WEB_DEMO"]
    line_experience: Literal["EXPERIMENTAL_MULTI_CHANNEL_PROTOTYPE"]
    portfolio_storage: Literal["BROWSER_SESSION_ONLY"]
    line_primary_cta: Literal[False]
    private_artifacts_packaged: Literal[False]
    track_a_mean_outer_spearman: Literal[0.194]
    track_a_top_decile_lift: Literal[1.354]
    track_a_outer_folds: Literal[7]
    current_market_gate_passed: Literal[6]
    current_market_gate_total: Literal[9]
    exact_feature_parity_passed: Literal[5]
    exact_feature_parity_total: Literal[23]

    @model_validator(mode="after")
    def validate_public_release_boundary(self) -> PublicWebDemoReleaseConfig:
        if self.fastapi_required or self.request_time_network_calls:
            raise ValueError("public release must remain fixture-only")
        if self.current_market_inference_enabled or self.price_direction_enabled:
            raise ValueError("unsupported current-market capability enabled")
        if self.line_primary_cta:
            raise ValueError("LINE cannot be the primary portfolio CTA")
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


class HistoricalTrackASnapshot(StrictModel):
    feature_session: str
    target_session: str
    score: float = Field(ge=0)
    historical_percentile: float = Field(ge=0, le=100)
    band: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    outer_fold: str


class HistoricalEventEvidence(StrictModel):
    published_at: str
    source_type: Literal["LICENSED_EVENT_METADATA_DERIVED_SUMMARY"]
    event_class: str
    event_count: int = Field(ge=1)
    summary: str
    reaction_magnitude_score: float = Field(ge=0)
    historical_percentile: float = Field(ge=0, le=100)
    communication_band: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    linguistic_sentiment_status: Literal["ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED"]
    raw_title_public: Literal[False]


class TickerEvidence(StrictModel):
    ticker: str
    company: str
    coverage: Literal["FULL_DEMO_READY", "PARTIAL_DEMO_READY", "UNAVAILABLE"]
    track_a: HistoricalTrackASnapshot | None
    event: HistoricalEventEvidence | None

    @model_validator(mode="after")
    def validate_coverage(self) -> TickerEvidence:
        if self.coverage == "FULL_DEMO_READY" and (self.track_a is None or self.event is None):
            raise ValueError("full demo coverage requires Track A and event evidence")
        if self.coverage == "UNAVAILABLE" and (self.track_a is not None or self.event is not None):
            raise ValueError("unavailable ticker cannot carry evidence")
        return self


class HistoricalEvidenceFixture(StrictModel):
    schema_version: Literal["controlled-historical-evidence-v1"]
    fixture_id: Literal["f7-f5-oof-b4-derived-public-v1"]
    controlled_historical_data: Literal[True]
    synthetic_data: Literal[False]
    current_market_inference: Literal[False]
    request_time_provider_calls: Literal[False]
    private_raw_content_included: Literal[False]
    selection_policy: str
    track_a_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    track_b_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tickers: list[TickerEvidence] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def validate_universe(self) -> HistoricalEvidenceFixture:
        ticker_values = [item.ticker for item in self.tickers]
        if len(ticker_values) != len(set(ticker_values)):
            raise ValueError("historical evidence tickers must be unique")
        return self


def load_dashboard_config(path: Path) -> DashboardDemoConfig:
    return DashboardDemoConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_public_release_config(path: Path) -> PublicWebDemoReleaseConfig:
    return PublicWebDemoReleaseConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_controlled_fixture(path: Path) -> ControlledDashboardFixture:
    return ControlledDashboardFixture.model_validate_json(path.read_text(encoding="utf-8"))


def load_historical_evidence_fixture(path: Path) -> HistoricalEvidenceFixture:
    return HistoricalEvidenceFixture.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_dashboard_config_sha256(config: DashboardDemoConfig) -> str:
    return _canonical_hash(config.model_dump(mode="json"))


def canonical_fixture_sha256(fixture: ControlledDashboardFixture) -> str:
    return _canonical_hash(fixture.model_dump(mode="json"))


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
