from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.demo_auth import DemoServiceAuthenticator
from backend.app.core.errors import ServiceUnavailableError
from backend.app.schemas.demo_sandbox import (
    DemoDeleteMeResponse,
    DemoFinancialIntelligenceResponse,
    DemoHoldingCreate,
    DemoHoldingUpdate,
    DemoMutationResponse,
    DemoPortfolioHealthResponse,
    DemoPortfolioResponse,
    DemoPrincipalResponse,
    DemoStockAnalysisResponse,
)
from backend.app.services.demo_sandbox import DemoSandboxPolicy, DemoSandboxService

router = APIRouter(prefix="/api/v1/demo", tags=["line-public-beta"])
DatabaseSession = Annotated[Session, Depends(get_db)]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@lru_cache
def get_demo_authenticator() -> DemoServiceAuthenticator:
    try:
        return DemoServiceAuthenticator(get_settings().demo_gas_service_token)
    except ValueError as error:
        raise ServiceUnavailableError(
            "public beta service authentication is unavailable"
        ) from error


def require_demo_principal(
    authenticator: Annotated[DemoServiceAuthenticator, Depends(get_demo_authenticator)],
    authorization: Annotated[str | None, Header()] = None,
    principal_id: Annotated[str | None, Header(alias="X-Demo-Principal-ID")] = None,
) -> str:
    return authenticator.verify(authorization, principal_id)


DemoPrincipalContext = Annotated[str, Depends(require_demo_principal)]


def get_demo_service(db: DatabaseSession) -> DemoSandboxService:
    settings = get_settings()
    universe_path = _resolve(settings.demo_universe_config_path)
    fixture_path = _resolve(settings.f11b_controlled_fixture_path)
    policy = DemoSandboxPolicy(
        retention_days=settings.demo_retention_days,
        max_holdings=settings.demo_max_holdings,
        max_shares=settings.demo_max_shares,
        max_average_cost=settings.demo_max_average_cost,
        per_user_requests_per_minute=settings.demo_per_user_requests_per_minute,
        global_requests_per_minute=settings.demo_global_requests_per_minute,
    )
    try:
        return DemoSandboxService.from_paths(
            db, universe_path=universe_path, fixture_path=fixture_path, policy=policy
        )
    except (OSError, ValueError) as error:
        raise ServiceUnavailableError(
            "public beta controlled configuration is unavailable"
        ) from error


DemoService = Annotated[DemoSandboxService, Depends(get_demo_service)]


@router.get("/me", response_model=DemoPrincipalResponse)
def get_demo_me(principal: DemoPrincipalContext, service: DemoService) -> DemoPrincipalResponse:
    return service.get_principal(principal)


@router.post("/me/disclosure", response_model=DemoMutationResponse)
def accept_demo_disclosure(
    principal: DemoPrincipalContext,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> DemoMutationResponse:
    return service.accept_disclosure(principal, idempotency_key)


@router.delete("/me", response_model=DemoDeleteMeResponse)
def delete_demo_me(
    principal: DemoPrincipalContext, service: DemoService
) -> DemoDeleteMeResponse:
    return service.delete_my_data(principal)


@router.get("/portfolio", response_model=DemoPortfolioResponse)
def get_demo_portfolio(
    principal: DemoPrincipalContext, service: DemoService
) -> DemoPortfolioResponse:
    return service.list_portfolio(principal)


@router.post(
    "/portfolio/holdings",
    response_model=DemoMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_demo_holding(
    values: DemoHoldingCreate,
    principal: DemoPrincipalContext,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> DemoMutationResponse:
    return service.create_holding(principal, idempotency_key, values)


@router.patch("/portfolio/holdings/{holding_id}", response_model=DemoMutationResponse)
def update_demo_holding(
    holding_id: str,
    values: DemoHoldingUpdate,
    principal: DemoPrincipalContext,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> DemoMutationResponse:
    return service.update_holding(principal, holding_id, idempotency_key, values)


@router.delete("/portfolio/holdings/{holding_id}", response_model=DemoMutationResponse)
def delete_demo_holding(
    holding_id: str,
    principal: DemoPrincipalContext,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
    version: Annotated[int, Query(ge=1)],
) -> DemoMutationResponse:
    return service.delete_holding(principal, holding_id, idempotency_key, version)


@router.post("/portfolio/health", response_model=DemoPortfolioHealthResponse)
def get_demo_portfolio_health(
    principal: DemoPrincipalContext, service: DemoService
) -> DemoPortfolioHealthResponse:
    return service.portfolio_health(principal)


@router.get("/research/stock-analysis/{ticker}", response_model=DemoStockAnalysisResponse)
def get_demo_stock_analysis(
    ticker: str, principal: DemoPrincipalContext, service: DemoService
) -> DemoStockAnalysisResponse:
    return service.stock_analysis(principal, ticker)


@router.get(
    "/research/intelligence/{ticker}", response_model=DemoFinancialIntelligenceResponse
)
def get_demo_financial_intelligence(
    ticker: str, principal: DemoPrincipalContext, service: DemoService
) -> DemoFinancialIntelligenceResponse:
    return service.financial_intelligence(principal, ticker)


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path
