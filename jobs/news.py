from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.core.database import SessionLocal
from backend.app.services.news import NewsIngestionService
from pipelines.news.matching import TickerMatcher
from pipelines.news.twse_material import TwseMaterialAnnouncementProvider
from pipelines.news.twse_rss import TwseNewsRssProvider

DEFAULT_ALIASES = Path("research/configs/ticker_aliases.example.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest public TWSE news metadata")
    parser.add_argument(
        "--source",
        choices=("all", "twse-material", "twse-rss"),
        default="all",
    )
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    matcher = TickerMatcher.from_file(args.aliases)
    provider_types = []
    if args.source in {"all", "twse-material"}:
        provider_types.append(TwseMaterialAnnouncementProvider)
    if args.source in {"all", "twse-rss"}:
        provider_types.append(TwseNewsRssProvider)

    output = []
    for provider_type in provider_types:
        with SessionLocal() as session, provider_type() as provider:
            result = NewsIngestionService(session, provider, matcher).ingest()
            output.append(result.__dict__)
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
