from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_user_access
from backend.app.core.database import get_db
from backend.app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioResponse,
    PortfolioSyncConfirmResponse,
    PortfolioSyncPreviewRequest,
    PortfolioSyncPreviewResponse,
)
from backend.app.services.portfolio import PortfolioService

router = APIRouter(prefix="/users/{user_id}", tags=["portfolio"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AuthorizedUser = Annotated[str, Depends(require_user_access)]


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(user_id: str, authorized_user: AuthorizedUser, db: DatabaseSession):
    return PortfolioService(db).get_portfolio(authorized_user)


@router.post(
    "/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_holding(
    user_id: str,
    values: HoldingCreate,
    authorized_user: AuthorizedUser,
    db: DatabaseSession,
):
    return PortfolioService(db).create_holding(authorized_user, values)


@router.patch("/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(
    user_id: str,
    holding_id: str,
    values: HoldingUpdate,
    authorized_user: AuthorizedUser,
    db: DatabaseSession,
):
    return PortfolioService(db).update_holding(authorized_user, holding_id, values)


@router.post(
    "/portfolio-sync/preview",
    response_model=PortfolioSyncPreviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def preview_portfolio_sync(
    user_id: str,
    values: PortfolioSyncPreviewRequest,
    authorized_user: AuthorizedUser,
    db: DatabaseSession,
):
    return PortfolioService(db).preview_sync(authorized_user, values)


@router.post(
    "/portfolio-sync/{operation_id}/confirm",
    response_model=PortfolioSyncConfirmResponse,
)
def confirm_portfolio_sync(
    user_id: str,
    operation_id: str,
    authorized_user: AuthorizedUser,
    db: DatabaseSession,
):
    return PortfolioService(db).confirm_sync(authorized_user, operation_id)
