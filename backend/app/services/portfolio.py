import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.errors import (
    ConflictError,
    ExpiredOperationError,
    NotFoundError,
)
from backend.app.models import Holding, PortfolioSyncOperation
from backend.app.repositories.portfolio import PortfolioRepository
from backend.app.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    PortfolioSyncConfirmResponse,
    PortfolioSyncPreviewRequest,
    PortfolioSyncPreviewResponse,
)

MAX_HOLDINGS = 10
SYNC_TTL_MINUTES = 15


class PortfolioService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = PortfolioRepository(session)

    def get_portfolio(self, user_id: str):
        self._require_user(user_id)
        portfolio = self.repository.get_default_portfolio(user_id)
        if portfolio is None:
            raise NotFoundError("default portfolio not found")
        portfolio.holdings.sort(key=lambda holding: holding.ticker)
        return portfolio

    def create_holding(self, user_id: str, values: HoldingCreate) -> Holding:
        portfolio = self.get_portfolio(user_id)
        if len(portfolio.holdings) >= MAX_HOLDINGS:
            raise ConflictError(f"portfolio cannot contain more than {MAX_HOLDINGS} holdings")
        if self.repository.get_holding_by_ticker(portfolio.id, values.ticker):
            raise ConflictError("holding already exists for this ticker")
        holding = Holding(portfolio_id=portfolio.id, **values.model_dump())
        self.session.add(holding)
        self._commit_or_conflict("holding could not be created")
        self.session.refresh(holding)
        return holding

    def update_holding(self, user_id: str, holding_id: str, values: HoldingUpdate) -> Holding:
        self._require_user(user_id)
        holding = self.repository.get_holding(user_id, holding_id)
        if holding is None:
            raise NotFoundError("holding not found")
        for field, value in values.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(holding, field, value)
        self._commit_or_conflict("holding could not be updated")
        self.session.refresh(holding)
        return holding

    def preview_sync(
        self,
        user_id: str,
        request: PortfolioSyncPreviewRequest,
    ) -> PortfolioSyncPreviewResponse:
        portfolio = self.get_portfolio(user_id)
        existing = {holding.ticker for holding in portfolio.holdings}
        incoming = {holding.ticker for holding in request.holdings}
        payload = [holding.model_dump(mode="json") for holding in request.holdings]
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        now = datetime.now(UTC)
        operation = PortfolioSyncOperation(
            portfolio_id=portfolio.id,
            payload=payload,
            payload_hash=hashlib.sha256(canonical_payload.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=SYNC_TTL_MINUTES),
        )
        self.session.add(operation)
        self._commit_or_conflict("sync preview could not be created")
        self.session.refresh(operation)
        return PortfolioSyncPreviewResponse(
            operation_id=operation.id,
            expires_at=operation.expires_at,
            additions=len(incoming - existing),
            updates=len(incoming & existing),
            removals=len(existing - incoming),
            holdings=request.holdings,
        )

    def confirm_sync(self, user_id: str, operation_id: str) -> PortfolioSyncConfirmResponse:
        self._require_user(user_id)
        operation = self.repository.get_sync_operation(user_id, operation_id)
        if operation is None:
            raise NotFoundError("sync operation not found")
        if operation.status == "confirmed":
            return self._confirm_response(user_id, operation, applied=False)
        if self._is_expired(operation.expires_at):
            operation.status = "expired"
            self.session.commit()
            raise ExpiredOperationError("sync operation has expired")

        requested = [HoldingCreate.model_validate(item) for item in operation.payload]
        portfolio = self.get_portfolio(user_id)
        existing = {holding.ticker: holding for holding in portfolio.holdings}
        incoming_tickers = {holding.ticker for holding in requested}

        for ticker, holding in existing.items():
            if ticker not in incoming_tickers:
                self.session.delete(holding)
        for values in requested:
            holding = existing.get(values.ticker)
            if holding is None:
                self.session.add(Holding(portfolio_id=portfolio.id, **values.model_dump()))
            else:
                for field, value in values.model_dump().items():
                    setattr(holding, field, value)

        operation.status = "confirmed"
        operation.confirmed_at = datetime.now(UTC)
        self._commit_or_conflict("portfolio sync could not be applied")
        return self._confirm_response(user_id, operation, applied=True)

    def _confirm_response(
        self,
        user_id: str,
        operation: PortfolioSyncOperation,
        *,
        applied: bool,
    ) -> PortfolioSyncConfirmResponse:
        portfolio = self.get_portfolio(user_id)
        return PortfolioSyncConfirmResponse(
            operation_id=operation.id,
            status=operation.status,
            applied=applied,
            portfolio=portfolio,
        )

    def _require_user(self, user_id: str) -> None:
        if self.repository.get_user(user_id) is None:
            raise NotFoundError("user not found")

    def _commit_or_conflict(self, message: str) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ConflictError(message) from error

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)
