from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    get_b5_intelligence_config,
    get_backend_integration_config,
    get_financial_nlp_intelligence_config,
    get_research_prediction_service,
)
from backend.app.core.database import get_db
from backend.app.core.errors import InvalidRequestError
from backend.app.schemas.research import (
    FinancialIntelligenceResponse,
    VolatilitySurprisePredictionRequest,
    VolatilitySurprisePredictionResponse,
)
from backend.app.services.intelligence import FinancialIntelligenceService
from backend.app.services.research_prediction import ResearchPredictionService
from pipelines.intelligence.b5_integration import B5IntelligenceConfig
from pipelines.intelligence.financial_nlp import FinancialNlpIntelligenceConfig
from research.planning.backend_integration import BackendIntegrationConfig

router = APIRouter(prefix="/api/v1/research", tags=["research"])
DatabaseSession = Annotated[Session, Depends(get_db)]
PredictionService = Annotated[
    ResearchPredictionService, Depends(get_research_prediction_service)
]
BackendConfig = Annotated[
    BackendIntegrationConfig, Depends(get_backend_integration_config)
]
IntelligenceConfig = Annotated[
    FinancialNlpIntelligenceConfig, Depends(get_financial_nlp_intelligence_config)
]
B5Config = Annotated[B5IntelligenceConfig, Depends(get_b5_intelligence_config)]


@router.post(
    "/volatility-surprise/predict",
    response_model=VolatilitySurprisePredictionResponse,
)
def predict_volatility_surprise(
    values: VolatilitySurprisePredictionRequest,
    service: PredictionService,
) -> VolatilitySurprisePredictionResponse:
    try:
        return service.predict(values)
    except ValueError as error:
        raise InvalidRequestError(str(error)) from error


@router.get(
    "/intelligence/{ticker}",
    response_model=FinancialIntelligenceResponse,
)
def get_financial_intelligence(
    ticker: str,
    db: DatabaseSession,
    backend_config: BackendConfig,
    intelligence_config: IntelligenceConfig,
    b5_config: B5Config,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    as_of_cutoff: datetime | None = None,
) -> FinancialIntelligenceResponse:
    try:
        return FinancialIntelligenceService(
            db, backend_config, intelligence_config, b5_config
        ).list_recent(ticker, limit=limit, as_of_cutoff=as_of_cutoff)
    except ValueError as error:
        raise InvalidRequestError(str(error)) from error
