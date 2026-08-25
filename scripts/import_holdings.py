"""One-time, local-only CSV import for a private portfolio.

The command defaults to validation-only mode. It accepts a pre-hashed LINE user ID and never
prints holding values. Place input files under the ignored `imports/` directory.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.models import Holding, Portfolio, User
from backend.app.schemas.portfolio import HoldingCreate

HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_COLUMNS = {
    "ticker",
    "name",
    "quantity",
    "cost_basis",
    "take_profit_pct",
    "stop_loss_pct",
}


def parse_csv(path: Path) -> list[HoldingCreate]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
        holdings = [HoldingCreate.model_validate(row) for row in reader]
    tickers = [holding.ticker for holding in holdings]
    if len(tickers) != len(set(tickers)):
        raise ValueError("input contains duplicate tickers")
    if len(holdings) > 10:
        raise ValueError("a portfolio may contain at most 10 holdings")
    return holdings


def apply_import(line_user_id_hash: str, holdings: list[HoldingCreate], *, is_demo: bool) -> str:
    if not HASH_PATTERN.fullmatch(line_user_id_hash):
        raise ValueError("line user ID hash must be a lowercase SHA-256 hex digest")
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.line_user_id_hash == line_user_id_hash))
        if user is None:
            user = User(line_user_id_hash=line_user_id_hash)
            session.add(user)
            session.flush()
        portfolio = session.scalar(
            select(Portfolio).where(Portfolio.user_id == user.id, Portfolio.name == "default")
        )
        if portfolio is None:
            portfolio = Portfolio(user_id=user.id, name="default", is_demo=is_demo)
            session.add(portfolio)
            session.flush()
        for existing in list(portfolio.holdings):
            session.delete(existing)
        session.flush()
        for values in holdings:
            session.add(Holding(portfolio_id=portfolio.id, **values.model_dump()))
        return user.id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or import a private holdings CSV")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--line-user-id-hash", required=True)
    parser.add_argument("--apply", action="store_true", help="write after successful validation")
    parser.add_argument("--demo", action="store_true", help="mark the portfolio as demo data")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        holdings = parse_csv(args.csv_path)
        if not HASH_PATTERN.fullmatch(args.line_user_id_hash):
            raise ValueError("line user ID hash must be a lowercase SHA-256 hex digest")
    except (OSError, ValueError, ValidationError) as error:
        print(f"Import validation failed: {error}")
        return 1

    if not args.apply:
        print(f"Validation passed for {len(holdings)} holdings; no data was written.")
        return 0

    user_id = apply_import(args.line_user_id_hash, holdings, is_demo=args.demo)
    print(f"Imported {len(holdings)} holdings for internal user {user_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
