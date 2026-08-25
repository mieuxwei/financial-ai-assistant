from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models import Base, Portfolio, User


@pytest.fixture
def db_session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = test_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def users(db_session: Session) -> tuple[User, User]:
    user_a = User(line_user_id_hash="a" * 64)
    user_b = User(line_user_id_hash="b" * 64)
    db_session.add_all([user_a, user_b])
    db_session.flush()
    db_session.add_all(
        [
            Portfolio(user_id=user_a.id, name="default"),
            Portfolio(user_id=user_b.id, name="default"),
        ]
    )
    db_session.commit()
    return user_a, user_b
