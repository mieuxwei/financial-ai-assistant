from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.research import (
    PredictionClaimBoundary,
    VolatilitySurprisePredictionRequest,
    VolatilitySurprisePredictionResponse,
)
from backend.app.services.tickers import normalize_ticker
from research.modeling.final_research_model import (
    predict_from_artifact,
    verify_model_artifact,
)
from research.planning.backend_integration import BackendIntegrationConfig


class ResearchPredictionService:
    def __init__(
        self,
        config: BackendIntegrationConfig,
        artifact: dict[str, object],
    ) -> None:
        verify_model_artifact(artifact)
        if artifact["sha256"] != config.f7_artifact_sha256:
            raise ValueError("F10/F7 artifact lineage mismatch")
        self.config = config
        self.artifact = artifact

    @classmethod
    def from_path(
        cls, config: BackendIntegrationConfig, artifact_path: Path
    ) -> ResearchPredictionService:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ValueError("F7 model artifact must be a JSON object")
        return cls(config, artifact)

    def predict(
        self, values: VolatilitySurprisePredictionRequest
    ) -> VolatilitySurprisePredictionResponse:
        ticker = normalize_ticker(values.ticker)
        result = predict_from_artifact(
            self.artifact,
            ticker,
            values.as_of_date.isoformat(),
            values.information_cutoff.isoformat(),
            values.features,
        )
        return VolatilitySurprisePredictionResponse(
            schema_version=self.config.prediction_response_version,
            **result,
            target_version=str(self.artifact["target_version"]),
            artifact_sha256=str(self.artifact["sha256"]),
            claim_boundary=PredictionClaimBoundary.model_validate(
                self.config.claim_boundary
            ),
        )
