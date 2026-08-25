from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.models import (
    DailySentimentAggregate,
    SentimentInferenceRun,
    SentimentResult,
)
from backend.app.repositories.sentiment import ArticleTickerPair, SentimentRepository
from pipelines.sentiment.base import SentimentModel
from pipelines.sentiment.text import (
    build_sentiment_text,
    sentiment_input_hash,
    supports_language,
)
from pipelines.sentiment.types import SentimentPrediction

TAIPEI = ZoneInfo("Asia/Taipei")
PROBABILITY_QUANTUM = Decimal("0.00000001")


@dataclass(frozen=True)
class SentimentInferenceResult:
    run_id: str
    status: str
    candidate_pairs: int
    scored_pairs: int
    existing_pairs: int
    skipped_language_pairs: int
    aggregate_rows: int


class SentimentInferenceService:
    def __init__(
        self,
        session: Session,
        model: SentimentModel,
        *,
        batch_size: int = 16,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least one")
        self.session = session
        self.model = model
        self.batch_size = batch_size
        self.repository = SentimentRepository(session)

    def run(self) -> SentimentInferenceResult:
        run = SentimentInferenceRun(model_version=self.model.model_version)
        self.session.add(run)
        self.session.commit()
        run_id = run.id
        try:
            pairs = self.repository.list_article_ticker_pairs()
            existing = self.repository.existing_pair_keys(self.model.model_version)
            pending = [
                pair
                for pair in pairs
                if (pair.article.id, pair.link.ticker) not in existing
            ]
            supported = [
                pair
                for pair in pending
                if supports_language(
                    pair.article.language, self.model.supported_language_prefixes
                )
            ]
            skipped_language = len(pending) - len(supported)
            scored_at = datetime.now(UTC)
            predictions = self._predict_unique_articles(supported)
            for pair in supported:
                prediction = predictions[pair.article.id]
                text = build_sentiment_text(pair.article.title, pair.article.summary)
                self.repository.add_result(
                    SentimentResult(
                        article_id=pair.article.id,
                        ticker=pair.link.ticker,
                        model_version=self.model.model_version,
                        positive_prob=_decimal(prediction.positive_prob),
                        neutral_prob=_decimal(prediction.neutral_prob),
                        negative_prob=_decimal(prediction.negative_prob),
                        sentiment_score=_decimal(prediction.score),
                        predicted_label=prediction.label,
                        input_hash=sentiment_input_hash(text, self.model.model_version),
                        scored_at=scored_at,
                    )
                )
            self.session.flush()
            aggregates = self._build_aggregates(scored_at)
            self.repository.replace_aggregates(self.model.model_version, aggregates)

            run.status = "succeeded"
            run.candidate_pairs = len(pairs)
            run.scored_pairs = len(supported)
            run.existing_pairs = len(pairs) - len(pending)
            run.skipped_language_pairs = skipped_language
            run.aggregate_rows = len(aggregates)
            run.quality_report = {
                "supported_language_prefixes": list(
                    self.model.supported_language_prefixes
                ),
                "unsupported_languages_are_neutral": False,
                "translation_used": False,
                "batch_size": self.batch_size,
            }
            run.completed_at = datetime.now(UTC)
            self.session.commit()
            return self._result(run)
        except Exception as error:
            self.session.rollback()
            failed = self.session.get(SentimentInferenceRun, run_id)
            if failed is not None:
                failed.status = "failed"
                failed.error_code = type(error).__name__
                failed.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    def _predict_unique_articles(
        self, pairs: list[ArticleTickerPair]
    ) -> dict[str, SentimentPrediction]:
        articles = {pair.article.id: pair.article for pair in pairs}
        ordered = [articles[key] for key in sorted(articles)]
        output: dict[str, SentimentPrediction] = {}
        for start in range(0, len(ordered), self.batch_size):
            batch = ordered[start : start + self.batch_size]
            texts = [build_sentiment_text(item.title, item.summary) for item in batch]
            predictions = self.model.predict_batch(texts)
            if len(predictions) != len(batch):
                raise ValueError("sentiment model returned an unexpected batch size")
            output.update(
                {
                    article.id: prediction
                    for article, prediction in zip(batch, predictions, strict=True)
                }
            )
        return output

    def _build_aggregates(self, aggregated_at: datetime) -> list[DailySentimentAggregate]:
        groups = defaultdict(list)
        for result, article, link in self.repository.rows_for_aggregation(
            self.model.model_version
        ):
            published_at = article.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)
            key = (link.ticker, published_at.astimezone(TAIPEI).date())
            groups[key].append((result, link))

        aggregates = []
        for (ticker, sentiment_date), rows in sorted(groups.items()):
            count = len(rows)
            weights = [Decimal(str(link.relevance_score)) for _, link in rows]
            weight_total = sum(weights, Decimal())
            scores = [result.sentiment_score for result, _ in rows]
            aggregates.append(
                DailySentimentAggregate(
                    ticker=ticker,
                    sentiment_date=sentiment_date,
                    model_version=self.model.model_version,
                    article_count=count,
                    positive_prob_mean=_mean(
                        [result.positive_prob for result, _ in rows]
                    ),
                    neutral_prob_mean=_mean(
                        [result.neutral_prob for result, _ in rows]
                    ),
                    negative_prob_mean=_mean(
                        [result.negative_prob for result, _ in rows]
                    ),
                    sentiment_score_mean=_mean(scores),
                    relevance_weighted_score=_decimal(
                        sum(
                            (
                                score * weight
                                for score, weight in zip(scores, weights, strict=True)
                            ),
                            Decimal(),
                        )
                        / weight_total
                    ),
                    positive_ratio=_decimal(
                        sum(result.predicted_label == "positive" for result, _ in rows)
                        / count
                    ),
                    negative_ratio=_decimal(
                        sum(result.predicted_label == "negative" for result, _ in rows)
                        / count
                    ),
                    aggregated_at=aggregated_at,
                )
            )
        return aggregates

    @staticmethod
    def _result(run: SentimentInferenceRun) -> SentimentInferenceResult:
        return SentimentInferenceResult(
            run_id=run.id,
            status=run.status,
            candidate_pairs=run.candidate_pairs,
            scored_pairs=run.scored_pairs,
            existing_pairs=run.existing_pairs,
            skipped_language_pairs=run.skipped_language_pairs,
            aggregate_rows=run.aggregate_rows,
        )


def _decimal(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(PROBABILITY_QUANTUM, rounding=ROUND_HALF_EVEN)


def _mean(values: list[Decimal]) -> Decimal:
    return _decimal(sum(values, Decimal()) / len(values))
