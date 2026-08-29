from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from backend.app.models import (
    DemoAuditEvent,
    DemoHolding,
    DemoIdempotencyRecord,
    DemoPrincipal,
)
from backend.app.repositories.demo_sandbox import DemoSandboxRepository
from backend.app.schemas.demo_sandbox import (
    DemoDeleteMeResponse,
    DemoFinancialIntelligenceResponse,
    DemoHoldingCreate,
    DemoHoldingResponse,
    DemoHoldingUpdate,
    DemoIntelligenceSignal,
    DemoMutationResponse,
    DemoPortfolioHealthItem,
    DemoPortfolioHealthResponse,
    DemoPortfolioResponse,
    DemoPrincipalResponse,
    DemoResearchSignal,
    DemoStockAnalysisResponse,
)
from demo.contracts import ControlledDashboardFixture, load_controlled_fixture

RETENTION_LIMITATION = (
    "Demo 持股最長保存 30 天；不連接券商、私人 Google Sheet 或即時市場資料。"
)
RESEARCH_LIMITATION = (
    "此模型研究下一交易日相對波動異常程度，不預測股價上漲或下跌；"
    "本頁為受控研究訊號，不是即時資料或投資建議。"
)
CHINESE_ABSTENTION = "中文文字情緒目前尚未通過獨立驗證。"


@dataclass(frozen=True)
class DemoSandboxPolicy:
    retention_days: int = 30
    max_holdings: int = 5
    max_shares: Decimal = Decimal("10000000")
    max_average_cost: Decimal = Decimal("1000000")
    per_user_requests_per_minute: int = 30
    global_requests_per_minute: int = 300


def load_demo_universe(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    universe = payload.get("universe")
    if not isinstance(universe, list) or len(universe) != 10:
        raise ValueError("frozen demo universe must contain exactly ten entries")
    result: dict[str, str] = {}
    for item in universe:
        if not isinstance(item, dict):
            raise ValueError("invalid frozen universe entry")
        ticker, name = item.get("ticker"), item.get("name")
        if not isinstance(ticker, str) or not isinstance(name, str):
            raise ValueError("invalid frozen universe identity")
        result[ticker] = name
    return result


class DemoSandboxService:
    def __init__(
        self,
        session: Session,
        *,
        universe: dict[str, str],
        fixture: ControlledDashboardFixture,
        policy: DemoSandboxPolicy | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.session = session
        self.repository = DemoSandboxRepository(session)
        self.universe = universe
        self.fixture = fixture
        self.policy = policy or DemoSandboxPolicy()
        self.now = now

    @classmethod
    def from_paths(
        cls,
        session: Session,
        *,
        universe_path: Path,
        fixture_path: Path,
        policy: DemoSandboxPolicy,
    ) -> DemoSandboxService:
        return cls(
            session,
            universe=load_demo_universe(universe_path),
            fixture=load_controlled_fixture(fixture_path),
            policy=policy,
        )

    def get_principal(self, principal_id: str) -> DemoPrincipalResponse:
        principal = self._prepare(principal_id, "get_principal")
        self._commit("principal could not be initialized")
        return DemoPrincipalResponse(
            disclosure_accepted=principal.disclosure_accepted_at is not None,
            expires_at=principal.expires_at,
        )

    def accept_disclosure(self, principal_id: str, key: str) -> DemoMutationResponse:
        principal = self._prepare(principal_id, "accept_disclosure")
        replay = self._replay(principal_id, key, "accept_disclosure", DemoMutationResponse)
        if replay is not None:
            return replay
        principal.disclosure_accepted_at = self.now()
        self._extend_expiry(principal)
        response = DemoMutationResponse(operation="disclosure_accepted", applied=True)
        self._record_idempotency(principal_id, key, "accept_disclosure", response)
        self._commit("disclosure acceptance could not be saved")
        return response

    def list_portfolio(self, principal_id: str) -> DemoPortfolioResponse:
        self._prepare(principal_id, "list_portfolio")
        holdings = self.repository.list_holdings(principal_id)
        self._commit("portfolio could not be read")
        return self._portfolio_response(holdings)

    def create_holding(
        self, principal_id: str, key: str, values: DemoHoldingCreate
    ) -> DemoMutationResponse:
        principal = self._prepare(principal_id, "create_holding")
        replay = self._replay(principal_id, key, "create_holding", DemoMutationResponse)
        if replay is not None:
            return replay
        self._validate_values(values.ticker, values.shares, values.average_cost)
        if principal.disclosure_accepted_at is None:
            raise ConflictError("demo disclosure must be accepted before adding holdings")
        if len(self.repository.list_holdings(principal_id)) >= self.policy.max_holdings:
            raise ConflictError(f"demo portfolio cannot exceed {self.policy.max_holdings} holdings")
        if self.repository.get_holding_by_ticker(principal_id, values.ticker) is not None:
            raise ConflictError("demo holding already exists for this ticker")
        expires_at = self._expiry()
        holding = DemoHolding(
            principal_id=principal_id,
            ticker=values.ticker,
            shares=values.shares,
            average_cost=values.average_cost,
            expires_at=expires_at,
        )
        self._extend_expiry(principal, expires_at)
        self.session.add(holding)
        self.session.flush()
        response = DemoMutationResponse(
            operation="created", applied=True, holding=self._holding_response(holding)
        )
        self._record_idempotency(principal_id, key, "create_holding", response)
        self._commit("demo holding could not be created")
        return response

    def update_holding(
        self,
        principal_id: str,
        holding_id: str,
        key: str,
        values: DemoHoldingUpdate,
    ) -> DemoMutationResponse:
        principal = self._prepare(principal_id, "update_holding")
        operation = f"update_holding:{holding_id}"
        replay = self._replay(principal_id, key, operation, DemoMutationResponse)
        if replay is not None:
            return replay
        self._validate_values(None, values.shares, values.average_cost)
        holding = self.repository.get_holding(principal_id, holding_id)
        if holding is None:
            raise NotFoundError("demo holding not found")
        if holding.version != values.version:
            raise ConflictError("demo holding version conflict")
        holding.shares = values.shares
        holding.average_cost = values.average_cost
        holding.version += 1
        holding.expires_at = self._expiry()
        self._extend_expiry(principal, holding.expires_at)
        self.session.flush()
        response = DemoMutationResponse(
            operation="updated", applied=True, holding=self._holding_response(holding)
        )
        self._record_idempotency(principal_id, key, operation, response)
        self._commit("demo holding could not be updated")
        return response

    def delete_holding(
        self, principal_id: str, holding_id: str, key: str, version: int
    ) -> DemoMutationResponse:
        principal = self._prepare(principal_id, "delete_holding")
        operation = f"delete_holding:{holding_id}"
        replay = self._replay(principal_id, key, operation, DemoMutationResponse)
        if replay is not None:
            return replay
        holding = self.repository.get_holding(principal_id, holding_id)
        if holding is None:
            raise NotFoundError("demo holding not found")
        if holding.version != version:
            raise ConflictError("demo holding version conflict")
        response = DemoMutationResponse(
            operation="deleted", applied=True, holding=self._holding_response(holding)
        )
        self.session.delete(holding)
        self._extend_expiry(principal)
        self._record_idempotency(principal_id, key, operation, response)
        self._commit("demo holding could not be deleted")
        return response

    def delete_my_data(self, principal_id: str) -> DemoDeleteMeResponse:
        principal = self.repository.get_principal(principal_id)
        if principal is None:
            return DemoDeleteMeResponse(deleted=False)
        self.session.delete(principal)
        self._commit("demo data could not be deleted")
        return DemoDeleteMeResponse(deleted=True)

    def portfolio_health(self, principal_id: str) -> DemoPortfolioHealthResponse:
        self._prepare(principal_id, "portfolio_health")
        items = [
            DemoPortfolioHealthItem(
                holding=self._holding_response(holding),
                research=self._research_signal(holding.ticker),
                intelligence=self._intelligence_signal(holding.ticker),
            )
            for holding in self.repository.list_holdings(principal_id)
        ]
        self._commit("portfolio health could not be assembled")
        return DemoPortfolioHealthResponse(items=items, limitation=RESEARCH_LIMITATION)

    def stock_analysis(self, principal_id: str, ticker: str) -> DemoStockAnalysisResponse:
        self._prepare(principal_id, "stock_analysis")
        company = self._company(ticker)
        self._commit("stock analysis could not be assembled")
        return DemoStockAnalysisResponse(
            ticker=ticker,
            company=company,
            research=self._research_signal(ticker),
            limitation=RESEARCH_LIMITATION,
        )

    def financial_intelligence(
        self, principal_id: str, ticker: str
    ) -> DemoFinancialIntelligenceResponse:
        self._prepare(principal_id, "financial_intelligence")
        company = self._company(ticker)
        self._commit("financial intelligence could not be assembled")
        return DemoFinancialIntelligenceResponse(
            ticker=ticker,
            company=company,
            intelligence=self._intelligence_signal(ticker),
            limitation=(
                "市場反應強度只代表歷史幅度關聯，不代表方向、因果或未來報酬。"
            ),
        )

    def cleanup_expired(self) -> int:
        expired = self.repository.expired_principals(self.now())
        for principal in expired:
            self.session.delete(principal)
        self._commit("expired demo data cleanup failed")
        return len(expired)

    def _prepare(self, principal_id: str, action: str) -> DemoPrincipal:
        principal = self.repository.get_principal(principal_id)
        if principal is None:
            principal = DemoPrincipal(id=principal_id, expires_at=self._expiry())
            self.session.add(principal)
            self.session.flush()
        since = self.now() - timedelta(minutes=1)
        if (
            self.repository.count_requests(principal_id=principal_id, since=since)
            >= self.policy.per_user_requests_per_minute
        ):
            raise ConflictError("demo command rate limit exceeded")
        if (
            self.repository.count_requests(principal_id=None, since=since)
            >= self.policy.global_requests_per_minute
        ):
            raise ConflictError("demo service rate limit exceeded")
        self.session.add(DemoAuditEvent(principal_id=principal_id, action=action))
        return principal

    def _replay(self, principal_id: str, key: str, operation: str, schema):
        record = self.repository.get_idempotency(principal_id, key)
        if record is None:
            return None
        if record.operation != operation:
            raise ConflictError("idempotency key was already used for another operation")
        return schema.model_validate(record.response_payload)

    def _record_idempotency(self, principal_id: str, key: str, operation: str, response) -> None:
        if not 16 <= len(key) <= 128:
            raise InvalidRequestError("idempotency key length is invalid")
        self.session.add(
            DemoIdempotencyRecord(
                principal_id=principal_id,
                idempotency_key=key,
                operation=operation,
                response_payload=response.model_dump(mode="json"),
            )
        )

    def _validate_values(
        self, ticker: str | None, shares: Decimal, average_cost: Decimal
    ) -> None:
        if ticker is not None:
            self._company(ticker)
        if shares > self.policy.max_shares:
            raise InvalidRequestError("shares exceed the demo ceiling")
        if average_cost > self.policy.max_average_cost:
            raise InvalidRequestError("average cost exceeds the demo ceiling")

    def _company(self, ticker: str) -> str:
        company = self.universe.get(ticker)
        if company is None:
            raise InvalidRequestError("ticker is outside the frozen research universe")
        return company

    def _portfolio_response(self, holdings: list[DemoHolding]) -> DemoPortfolioResponse:
        return DemoPortfolioResponse(
            max_holdings=self.policy.max_holdings,
            retention_days=self.policy.retention_days,
            holdings=[self._holding_response(item) for item in holdings],
            limitation=RETENTION_LIMITATION,
        )

    def _holding_response(self, holding: DemoHolding) -> DemoHoldingResponse:
        return DemoHoldingResponse(
            id=holding.id,
            ticker=holding.ticker,
            company=self._company(holding.ticker),
            shares=holding.shares,
            average_cost=holding.average_cost,
            created_at=holding.created_at,
            updated_at=holding.updated_at,
            expires_at=holding.expires_at,
            version=holding.version,
        )

    def _research_signal(self, ticker: str) -> DemoResearchSignal:
        if ticker != self.fixture.prediction_request.ticker:
            return DemoResearchSignal(
                status="UNAVAILABLE_FOR_CONTROLLED_FIXTURE",
                fixture_id=None,
                score=None,
                historical_percentile=None,
                communication_band=None,
            )
        prediction = self.fixture.prediction_response
        return DemoResearchSignal(
            status="CONTROLLED_RESEARCH_SIGNAL",
            fixture_id=self.fixture.fixture_id,
            score=float(prediction.predicted_volatility_surprise),
            historical_percentile=prediction.historical_percentile,
            communication_band=prediction.risk_band,
        )

    def _intelligence_signal(self, ticker: str) -> DemoIntelligenceSignal:
        if ticker != self.fixture.prediction_request.ticker:
            return DemoIntelligenceSignal(
                status="UNAVAILABLE_FOR_CONTROLLED_FIXTURE",
                event_class=None,
                event_summary=None,
                market_reaction_magnitude=None,
                chinese_sentiment_message=CHINESE_ABSTENTION,
            )
        chinese = next(
            item for item in self.fixture.intelligence_items if item.language.startswith("zh")
        )
        b5 = chinese.track_b_intelligence
        return DemoIntelligenceSignal(
            status="CONTROLLED_RESEARCH_INTELLIGENCE",
            event_class=b5.event_classification.event_class if b5 else None,
            event_summary=chinese.source_excerpt,
            market_reaction_magnitude=(
                b5.market_reaction.communication_band if b5 and b5.market_reaction else None
            ),
            chinese_sentiment_message=CHINESE_ABSTENTION,
        )

    def _expiry(self) -> datetime:
        return self.now() + timedelta(days=self.policy.retention_days)

    def _extend_expiry(
        self, principal: DemoPrincipal, expires_at: datetime | None = None
    ) -> None:
        value = expires_at or self._expiry()
        principal.expires_at = value
        for holding in self.repository.list_holdings(principal.id):
            holding.expires_at = value

    def _commit(self, message: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ConflictError(message) from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ConflictError(message) from error
