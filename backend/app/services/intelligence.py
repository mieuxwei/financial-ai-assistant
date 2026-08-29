from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.core.errors import ServiceUnavailableError
from backend.app.repositories.intelligence import IntelligenceRepository
from backend.app.schemas.research import (
    FinancialIntelligenceItem,
    FinancialIntelligenceResponse,
    IntelligenceRetrievalBoundary,
)
from backend.app.services.tickers import normalize_ticker
from pipelines.intelligence.b5_integration import (
    B5IntelligenceConfig,
    assemble_b5_intelligence,
)
from pipelines.intelligence.financial_nlp import (
    FinancialNlpIntelligenceConfig,
    assemble_intelligence_item,
)
from pipelines.news.types import NewsItem, TickerMatch
from pipelines.sentiment.text import build_sentiment_text, sentiment_input_hash
from pipelines.sentiment.types import SentimentPrediction
from research.planning.backend_integration import BackendIntegrationConfig


class FinancialIntelligenceService:
    def __init__(
        self,
        session: Session,
        backend_config: BackendIntegrationConfig,
        intelligence_config: FinancialNlpIntelligenceConfig,
        b5_config: B5IntelligenceConfig,
    ) -> None:
        if intelligence_config.canonical_sha256 != backend_config.f8_config_sha256:
            raise ValueError("F10/F8 intelligence-config lineage mismatch")
        self.repository = IntelligenceRepository(session)
        self.backend_config = backend_config
        self.intelligence_config = intelligence_config
        if b5_config.f8_config_canonical_sha256 != intelligence_config.canonical_sha256:
            raise ValueError("B5/F8 intelligence-config lineage mismatch")
        self.b5_config = b5_config

    def list_recent(
        self,
        ticker: str,
        *,
        limit: int,
        as_of_cutoff: datetime | None,
    ) -> FinancialIntelligenceResponse:
        normalized_ticker = normalize_ticker(ticker)
        if as_of_cutoff is not None and (
            as_of_cutoff.tzinfo is None or as_of_cutoff.utcoffset() is None
        ):
            raise ValueError("as_of_cutoff must be timezone-aware")
        rows = self.repository.list_recent(
            ticker=normalized_ticker,
            model_version=self.intelligence_config.english_model_version,
            limit=limit,
            as_of_cutoff=as_of_cutoff,
        )
        items = []
        for row in rows:
            published_at = row.article.published_at
            if published_at.tzinfo is None or published_at.utcoffset() is None:
                published_at = published_at.replace(tzinfo=UTC)
            metadata = row.article.source_metadata or {}
            item = NewsItem(
                title=row.article.title,
                published_at=published_at,
                source=row.article.source,
                source_type=row.article.source_type,
                url=row.article.url,
                summary=row.article.summary,
                language=row.article.language,
                external_id=row.article.external_id,
                explicit_tickers=(normalized_ticker,),
                metadata={
                    key: _optional_string(metadata.get(key))
                    for key in ("company_name", "clause", "fact_date")
                },
            )
            prediction = None
            model_version = None
            if row.sentiment is not None:
                expected_input_hash = sentiment_input_hash(
                    build_sentiment_text(item.title, item.summary),
                    row.sentiment.model_version,
                )
                if row.sentiment.input_hash != expected_input_hash:
                    raise ServiceUnavailableError(
                        "stored financial intelligence lineage is invalid"
                    )
                prediction = SentimentPrediction(
                    positive_prob=float(row.sentiment.positive_prob),
                    neutral_prob=float(row.sentiment.neutral_prob),
                    negative_prob=float(row.sentiment.negative_prob),
                )
                model_version = row.sentiment.model_version
            assembled = assemble_intelligence_item(
                self.intelligence_config,
                item,
                [
                    TickerMatch(
                        ticker=row.link.ticker,
                        relevance_score=float(row.link.relevance_score),
                        match_method=row.link.match_method,
                    )
                ],
                sentiment_prediction=prediction,
                sentiment_model_version=model_version,
            )
            assembled["track_b_intelligence"] = assemble_b5_intelligence(
                self.b5_config,
                source=item.source,
                source_type=item.source_type,
                published_at=item.published_at,
                language=item.language,
                metadata=metadata,
                requested_cutoff=as_of_cutoff,
            )
            items.append(FinancialIntelligenceItem.model_validate(assembled))
        return FinancialIntelligenceResponse(
            schema_version=self.backend_config.intelligence_response_version,
            ticker=normalized_ticker,
            as_of_cutoff=as_of_cutoff,
            item_count=len(items),
            items=items,
            intelligence_version=self.intelligence_config.intelligence_version,
            config_sha256=self.intelligence_config.canonical_sha256,
            retrieval_boundary=IntelligenceRetrievalBoundary(
                database_only=True,
                external_api_called=False,
                model_inference_performed=False,
                llm_called=False,
                full_article_content_returned=False,
            ),
            disclaimer=(
                "此結果為研究型歷史關聯訊號，不代表投資建議、因果關係或未來報酬保證；"
                "中文文字情緒目前尚未通過獨立驗證。"
            ),
        )


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
