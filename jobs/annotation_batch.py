from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import inspect, select

from backend.app.core.database import SessionLocal
from backend.app.models import ArticleTicker, NewsArticle
from research.annotation.calibration_batch import (
    AnnouncementCandidate,
    build_calibration_batch,
    write_calibration_batch,
)

DEFAULT_EXCLUSIONS = Path("research/evaluation/twse_announcement_sentiment_samples.json")
DEFAULT_OUTPUT = Path("artifacts/twse-calibration-batch.jsonl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export an unlabeled, leakage-safe TWSE calibration batch"
    )
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--exclude-samples", type=Path, default=DEFAULT_EXCLUSIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def load_excluded_texts(path: Path) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("excluded sample file must contain a JSON array")
    return [str(row["text"]) for row in payload if isinstance(row, dict) and row.get("text")]


def main() -> int:
    args = build_parser().parse_args()
    with SessionLocal() as session:
        inspector = inspect(session.get_bind())
        required_tables = {"news_articles", "article_tickers"}
        missing_tables = sorted(
            table for table in required_tables if not inspector.has_table(table)
        )
        if missing_tables:
            print(
                json.dumps(
                    {
                        "status": "database_not_ready",
                        "missing_tables": missing_tables,
                        "next_command": "alembic upgrade head",
                    },
                    ensure_ascii=False,
                )
            )
            return 3
        records = session.execute(
            select(NewsArticle, ArticleTicker)
            .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
            .where(
                NewsArticle.source == "twse_material",
                NewsArticle.source_type == "official_announcement",
            )
            .order_by(NewsArticle.published_at, NewsArticle.id, ArticleTicker.ticker)
        ).all()
        candidates = [
            AnnouncementCandidate(
                source=article.source,
                source_type=article.source_type,
                source_url=article.url,
                source_record_id=article.external_id,
                published_at=article.published_at,
                ticker=link.ticker,
                entity_name=str((article.source_metadata or {}).get("company_name") or link.ticker),
                title=article.title,
                context=article.summary,
                content_hash=article.content_hash,
                title_fingerprint=article.title_fingerprint,
            )
            for article, link in records
        ]

    rows = build_calibration_batch(
        candidates,
        limit=args.limit,
        excluded_texts=load_excluded_texts(args.exclude_samples),
    )
    write_calibration_batch(args.output, rows)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "row_count": len(rows),
                "requested_count": args.limit,
                "contains_labels": False,
                "contains_future_returns": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if len(rows) == args.limit else 2


if __name__ == "__main__":
    raise SystemExit(main())
