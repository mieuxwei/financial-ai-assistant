from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BackendIntegrationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["backend-integration-config-v1"]
    api_version: Literal["financial-research-api-v1"]
    prediction_response_version: Literal["volatility-surprise-prediction-response-v1"]
    intelligence_response_version: Literal["financial-intelligence-response-v1"]
    prediction_endpoint: Literal["/api/v1/research/volatility-surprise/predict"]
    intelligence_endpoint: Literal["/api/v1/research/intelligence/{ticker}"]
    f7_artifact_path: str
    f7_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    f8_config_path: str
    f8_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prediction_input: dict[str, Any]
    intelligence_retrieval: dict[str, Any]
    claim_boundary: dict[str, bool]
    artifact_loading: Literal["LAZY_FAIL_CLOSED"]
    authentication_scope: Literal["PUBLIC_RESEARCH_NO_PRIVATE_PORTFOLIO_DATA"]
    modify_gas_in_f10: Literal[False]
    external_api_calls_in_f10_audit: Literal[False]
    model_training_in_f10: Literal[False]
    deploy_in_f10: Literal[False]

    @model_validator(mode="after")
    def validate_f10_boundaries(self) -> BackendIntegrationConfig:
        if self.f7_artifact_path != ".tools/models/f7-final-ridge-research-v1/model.json":
            raise ValueError("F10 frozen F7 artifact path drifted")
        if self.f8_config_path != "research/configs/financial_nlp_intelligence.v1.json":
            raise ValueError("F10 frozen F8 config path drifted")
        expected_prediction = {
            "feature_contract": "risk-features-v1",
            "exact_feature_set_required": True,
            "timezone_aware_cutoff_required": True,
            "server_computes_features_in_f10": False,
        }
        if self.prediction_input != expected_prediction:
            raise ValueError("F10 prediction-input boundary drifted")
        expected_retrieval = {
            "database_only": True,
            "external_fetch_on_request": False,
            "model_inference_on_request": False,
            "llm_on_request": False,
            "default_limit": 10,
            "maximum_limit": 50,
        }
        if self.intelligence_retrieval != expected_retrieval:
            raise ValueError("F10 intelligence-retrieval boundary drifted")
        expected_claims = {
            "research_signal_only": True,
            "prospective_accuracy": False,
            "price_direction_forecast": False,
            "investment_advice": False,
            "guaranteed_future_volatility": False,
        }
        if self.claim_boundary != expected_claims:
            raise ValueError("F10 claim boundary drifted")
        return self


def load_backend_integration_config(path: Path) -> BackendIntegrationConfig:
    return BackendIntegrationConfig.model_validate_json(path.read_text(encoding="utf-8"))


def canonical_f10_config_sha256(config: BackendIntegrationConfig) -> str:
    payload = json.dumps(
        config.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
