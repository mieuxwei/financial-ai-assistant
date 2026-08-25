from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Holding, Portfolio, PortfolioSyncOperation, User


class PortfolioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_default_portfolio(self, user_id: str) -> Portfolio | None:
        statement: Select[tuple[Portfolio]] = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id, Portfolio.name == "default")
            .options(selectinload(Portfolio.holdings))
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(statement)

    def get_holding(self, user_id: str, holding_id: str) -> Holding | None:
        statement = (
            select(Holding)
            .join(Portfolio)
            .where(Holding.id == holding_id, Portfolio.user_id == user_id)
        )
        return self.session.scalar(statement)

    def get_holding_by_ticker(self, portfolio_id: str, ticker: str) -> Holding | None:
        return self.session.scalar(
            select(Holding).where(
                Holding.portfolio_id == portfolio_id,
                Holding.ticker == ticker,
            )
        )

    def get_sync_operation(self, user_id: str, operation_id: str) -> PortfolioSyncOperation | None:
        statement = (
            select(PortfolioSyncOperation)
            .join(Portfolio)
            .where(
                PortfolioSyncOperation.id == operation_id,
                Portfolio.user_id == user_id,
            )
            .options(selectinload(PortfolioSyncOperation.portfolio))
        )
        return self.session.scalar(statement)
