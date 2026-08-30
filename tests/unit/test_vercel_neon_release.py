from pathlib import Path

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine
from scripts import vercel_build

ROOT = Path(__file__).resolve().parents[2]


def test_neon_standard_url_uses_declared_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://localhost/demo")
    assert settings.resolved_database_url.startswith("postgresql+psycopg://")
    engine = create_database_engine(settings.resolved_database_url)
    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()


def test_vercel_release_uses_fastapi_entrypoint_and_singapore_region() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    vercel = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert 'entrypoint = "backend.app.main:app"' in pyproject
    assert 'build = "python scripts/vercel_build.py"' in pyproject
    assert '"regions": ["sin1"]' in vercel


def test_vercel_preview_build_never_migrates(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def unexpected_upgrade(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(vercel_build.command, "upgrade", unexpected_upgrade)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    vercel_build.main()
    assert called is False


def test_vercel_production_build_fails_closed_without_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///unsafe-production.db")
    with pytest.raises(RuntimeError, match="requires a PostgreSQL DATABASE_URL"):
        vercel_build.main()
