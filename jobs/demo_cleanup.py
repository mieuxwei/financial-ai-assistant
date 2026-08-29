from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.repositories.demo_sandbox import DemoSandboxRepository


def main() -> None:
    """Delete expired public-beta principals and all cascaded sandbox content."""
    from datetime import UTC, datetime

    with SessionLocal() as session:
        repository = DemoSandboxRepository(session)
        expired = repository.expired_principals(datetime.now(UTC))
        for principal in expired:
            session.delete(principal)
        session.commit()
    print(f"Expired demo principals removed: {len(expired)}")


if __name__ == "__main__":
    get_settings()
    main()
