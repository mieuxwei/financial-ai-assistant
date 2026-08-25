from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models import NewsArticle, NewsIngestionRun
from backend.app.repositories.news import NewsRepository
from pipelines.news.base import NewsProvider
from pipelines.news.matching import TickerMatcher
from pipelines.news.normalization import (
    canonicalize_url,
    content_hash,
    title_fingerprint,
)


@dataclass(frozen=True)
class NewsIngestionResult:
    run_id: str
    status: str
    records_fetched: int
    records_inserted: int
    exact_duplicates: int
    fuzzy_duplicates: int
    ticker_matches: int


class NewsIngestionService:
    def __init__(
        self, session: Session, provider: NewsProvider, matcher: TickerMatcher
    ) -> None:
        self.session = session
        self.provider = provider
        self.matcher = matcher
        self.repository = NewsRepository(session)

    def ingest(self) -> NewsIngestionResult:
        run = NewsIngestionRun(provider=self.provider.name)
        self.session.add(run)
        self.session.commit()
        run_id = run.id
        fetched_count = 0
        inserted_count = 0
        exact_duplicates = 0
        fuzzy_duplicates = 0
        ticker_matches = 0
        matched_articles = 0
        try:
            items = self.provider.fetch()
            fetched_count = len(items)
            fetched_at = datetime.now(UTC)
            for item in items:
                canonical_url = canonicalize_url(item.url)
                digest = content_hash(
                    item.title,
                    canonical_url,
                    item.published_at.isoformat(),
                    item.external_id,
                )
                if self.repository.find_exact(digest):
                    exact_duplicates += 1
                    continue
                if not item.explicit_tickers and self.repository.find_fuzzy(
                    title=item.title, published_at=item.published_at
                ):
                    fuzzy_duplicates += 1
                    continue
                matches = self.matcher.match(item)
                article = NewsArticle(
                    title=item.title.strip(),
                    published_at=item.published_at,
                    fetched_at=fetched_at,
                    source=item.source,
                    source_type=item.source_type,
                    url=item.url,
                    canonical_url=canonical_url,
                    summary=item.summary[:500] if item.summary else None,
                    content_hash=digest,
                    title_fingerprint=title_fingerprint(item.title),
                    language=item.language,
                    external_id=item.external_id,
                    source_metadata=item.metadata or None,
                )
                self.repository.add_article(article, matches)
                inserted_count += 1
                ticker_matches += len(matches)
                matched_articles += bool(matches)

            run.status = "succeeded"
            run.records_fetched = fetched_count
            run.records_inserted = inserted_count
            run.exact_duplicates = exact_duplicates
            run.fuzzy_duplicates = fuzzy_duplicates
            run.ticker_matches = ticker_matches
            run.quality_report = {
                "unmatched_articles": inserted_count - matched_articles,
                "summary_max_characters": 500,
                "full_article_content_stored": False,
            }
            run.completed_at = datetime.now(UTC)
            self.session.commit()
            return self._result(run)
        except Exception as error:
            self.session.rollback()
            failed_run = self.session.get(NewsIngestionRun, run_id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.records_fetched = fetched_count
                failed_run.error_code = type(error).__name__
                failed_run.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    @staticmethod
    def _result(run: NewsIngestionRun) -> NewsIngestionResult:
        return NewsIngestionResult(
            run_id=run.id,
            status=run.status,
            records_fetched=run.records_fetched,
            records_inserted=run.records_inserted,
            exact_duplicates=run.exact_duplicates,
            fuzzy_duplicates=run.fuzzy_duplicates,
            ticker_matches=run.ticker_matches,
        )
