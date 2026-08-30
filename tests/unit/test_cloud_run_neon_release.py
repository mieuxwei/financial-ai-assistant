from pathlib import Path

from backend.app.core.database import create_database_engine

ROOT = Path(__file__).resolve().parents[2]


def test_neon_standard_url_uses_declared_psycopg_driver() -> None:
    engine = create_database_engine("postgresql://demo:demo@localhost/demo")
    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()


def test_cloud_run_container_is_bounded_and_runs_migrations() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    setup = (ROOT / "docs/line_public_beta_setup.md").read_text(encoding="utf-8")
    assert "python:3.12-slim" in dockerfile
    assert "alembic upgrade head" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "minimum instances `0`" in setup
    assert "maximum instances `1`" in setup


def test_container_context_excludes_private_and_secret_paths() -> None:
    ignored = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    required = {
        ".env",
        ".env.*",
        ".tools",
        "data/private",
        "uploads",
        "user_data",
        "broker_screenshots",
        ".clasp.json",
    }
    assert required <= ignored
