"""Apply production database migrations during a Vercel build."""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config


def main() -> None:
    """Migrate only production against an explicitly configured PostgreSQL database."""
    if os.getenv("VERCEL_ENV") != "production":
        print("Skipping database migration outside the Vercel production environment.")
        return

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Production Vercel build requires a PostgreSQL DATABASE_URL.")

    command.upgrade(Config("alembic.ini"), "head")
    print("Production database migration completed.")


if __name__ == "__main__":
    main()
