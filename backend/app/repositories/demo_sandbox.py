from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import DemoAuditEvent, DemoHolding, DemoIdempotencyRecord, DemoPrincipal


class DemoSandboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_principal(self, principal_id: str) -> DemoPrincipal | None:
        return self.session.get(DemoPrincipal, principal_id)

    def list_holdings(self, principal_id: str) -> list[DemoHolding]:
        return list(
            self.session.scalars(
                select(DemoHolding)
                .where(DemoHolding.principal_id == principal_id)
                .order_by(DemoHolding.ticker)
            )
        )

    def get_holding(self, principal_id: str, holding_id: str) -> DemoHolding | None:
        return self.session.scalar(
            select(DemoHolding).where(
                DemoHolding.id == holding_id, DemoHolding.principal_id == principal_id
            )
        )

    def get_holding_by_ticker(self, principal_id: str, ticker: str) -> DemoHolding | None:
        return self.session.scalar(
            select(DemoHolding).where(
                DemoHolding.principal_id == principal_id, DemoHolding.ticker == ticker
            )
        )

    def get_idempotency(self, principal_id: str, key: str) -> DemoIdempotencyRecord | None:
        return self.session.scalar(
            select(DemoIdempotencyRecord).where(
                DemoIdempotencyRecord.principal_id == principal_id,
                DemoIdempotencyRecord.idempotency_key == key,
            )
        )

    def count_requests(self, *, principal_id: str | None, since: datetime) -> int:
        statement = select(func.count()).select_from(DemoAuditEvent).where(
            DemoAuditEvent.created_at >= since
        )
        if principal_id is not None:
            statement = statement.where(DemoAuditEvent.principal_id == principal_id)
        return int(self.session.scalar(statement) or 0)

    def expired_principals(self, now: datetime) -> list[DemoPrincipal]:
        return list(
            self.session.scalars(select(DemoPrincipal).where(DemoPrincipal.expires_at < now))
        )
