from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Header

from backend.app.core.config import get_settings
from backend.app.core.errors import ForbiddenError, ServiceUnavailableError
from backend.app.services.research_prediction import ResearchPredictionService
from pipelines.intelligence.financial_nlp import (
    FinancialNlpIntelligenceConfig,
    load_financial_nlp_intelligence_config,
)
from research.planning.backend_integration import (
    BackendIntegrationConfig,
    load_backend_integration_config,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def require_user_access(
    user_id: str,
    x_user_id: Annotated[str, Header(alias="X-User-ID")],
) -> str:
    """Transitional identity boundary until M10 verifies LINE signatures directly."""
    if x_user_id != user_id:
        raise ForbiddenError("requested user does not match the authenticated user context")
    return user_id


@lru_cache
def get_backend_integration_config() -> BackendIntegrationConfig:
    path = _resolve_repository_path(get_settings().backend_integration_config_path)
    try:
        return load_backend_integration_config(path)
    except (OSError, ValueError) as error:
        raise ServiceUnavailableError("research API configuration is unavailable") from error


@lru_cache
def get_financial_nlp_intelligence_config() -> FinancialNlpIntelligenceConfig:
    backend_config = get_backend_integration_config()
    path = _resolve_repository_path(backend_config.f8_config_path)
    try:
        return load_financial_nlp_intelligence_config(path)
    except (OSError, ValueError) as error:
        raise ServiceUnavailableError(
            "financial intelligence configuration is unavailable"
        ) from error


@lru_cache
def get_research_prediction_service() -> ResearchPredictionService:
    config = get_backend_integration_config()
    path = _resolve_repository_path(get_settings().final_model_artifact_path)
    try:
        return ResearchPredictionService.from_path(config, path)
    except (OSError, ValueError) as error:
        raise ServiceUnavailableError("frozen research model is unavailable") from error


def _resolve_repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path
