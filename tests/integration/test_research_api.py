from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_research_prediction_service
from backend.app.core.errors import ServiceUnavailableError
from backend.app.main import app
from backend.app.models import ArticleTicker, NewsArticle, SentimentResult
from backend.app.services.research_prediction import ResearchPredictionService
from pipelines.features.risk_builder import FEATURE_NAMES
from pipelines.sentiment.finbert import DEFAULT_MODEL_ID, DEFAULT_MODEL_REVISION
from pipelines.sentiment.text import build_sentiment_text, sentiment_input_hash
from research.modeling.final_research_model import ARTIFACT_VERSION
from research.planning.backend_integration import load_backend_integration_config

ROOT = Path(__file__).resolve().parents[2]
F10_CONFIG = ROOT / "research/configs/backend_integration.v1.json"
FINBERT_VERSION = f"{DEFAULT_MODEL_ID}@{DEFAULT_MODEL_REVISION}"


def _hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _artifact() -> dict[str, object]:
    size = len(FEATURE_NAMES)
    content = {
        "schema_version": ARTIFACT_VERSION,
        "inference_contract_version": "volatility-surprise-inference-v1",
        "artifact_format": "SAFE_JSON_NO_PICKLE",
        "model_name": "ridge_regression",
        "model_version": ARTIFACT_VERSION,
        "feature_pipeline_version": "risk-features-v1",
        "feature_names": list(FEATURE_NAMES),
        "target_version": "next_session_stock_normalized_abs_log_return_v1",
        "target_transform": "log1p",
        "inverse_transform": "maximum_zero_expm1",
        "prediction_quantum": "0.000000000001",
        "selected_hyperparameters": {"alpha": 100.0},
        "scaler_mean": [0.0] * size,
        "scaler_scale": [1.0] * size,
        "coefficient": [1.0] + [0.0] * (size - 1),
        "intercept": 0.0,
        "historical_reference": {
            "row_count": 3,
            "percentile_output_decimals": 6,
            "band_cutoffs": ["0.500000000000", "0.800000000000", "0.950000000000"],
            "band_labels": ["LOW", "MODERATE", "HIGH", "VERY_HIGH"],
            "sorted_predictions": ["0.000000000000", "0.500000000000", "1.000000000000"],
        },
        "lineage": {},
        "training": {},
        "research_claim_boundary": {},
        "final_model_selected": True,
        "model_artifact_persisted": True,
        "deployed": False,
        "m7_rerun_performed": False,
    }
    return {**content, "sha256": _hash(content)}


def _prediction_payload() -> dict[str, object]:
    features = {name: 0.0 for name in FEATURE_NAMES}
    features[FEATURE_NAMES[0]] = math.log(2)
    return {
        "ticker": "2330.tw",
        "as_of_date": "2026-08-28",
        "information_cutoff": "2026-08-28T13:30:00+08:00",
        "features": features,
    }


def _override_prediction_service() -> ResearchPredictionService:
    artifact = _artifact()
    config = load_backend_integration_config(F10_CONFIG).model_copy(
        update={"f7_artifact_sha256": artifact["sha256"]}
    )
    return ResearchPredictionService(config, artifact)


def test_prediction_endpoint_returns_frozen_score_lineage_and_claims(
    client: TestClient,
) -> None:
    app.dependency_overrides[get_research_prediction_service] = _override_prediction_service

    response = client.post(
        "/api/v1/research/volatility-surprise/predict", json=_prediction_payload()
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "2330"
    assert payload["predicted_volatility_surprise"] == "1.000000000000"
    assert payload["historical_percentile"] == 100.0
    assert payload["risk_band"] == "VERY_HIGH"
    assert payload["target_version"] == "next_session_stock_normalized_abs_log_return_v1"
    assert payload["claim_boundary"] == {
        "research_signal_only": True,
        "prospective_accuracy": False,
        "price_direction_forecast": False,
        "investment_advice": False,
        "guaranteed_future_volatility": False,
    }


def test_prediction_endpoint_rejects_feature_or_cutoff_drift(client: TestClient) -> None:
    app.dependency_overrides[get_research_prediction_service] = _override_prediction_service
    missing_feature = _prediction_payload()
    missing_feature["features"].pop(FEATURE_NAMES[-1])
    naive_cutoff = _prediction_payload()
    naive_cutoff["information_cutoff"] = "2026-08-28T13:30:00"

    missing_response = client.post(
        "/api/v1/research/volatility-surprise/predict", json=missing_feature
    )
    cutoff_response = client.post(
        "/api/v1/research/volatility-surprise/predict", json=naive_cutoff
    )

    assert missing_response.status_code == 422
    assert cutoff_response.status_code == 422
    assert missing_response.json()["error"]["code"] == "validation_error"


def test_prediction_endpoint_fails_closed_when_artifact_is_unavailable(
    client: TestClient,
) -> None:
    def unavailable() -> ResearchPredictionService:
        raise ServiceUnavailableError("frozen research model is unavailable")

    app.dependency_overrides[get_research_prediction_service] = unavailable
    response = client.post(
        "/api/v1/research/volatility-surprise/predict", json=_prediction_payload()
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "frozen research model is unavailable",
        }
    }


def test_intelligence_endpoint_returns_database_only_scored_and_abstained_items(
    client: TestClient,
    db_session: Session,
) -> None:
    english = NewsArticle(
        title="Company reports quarterly results",
        published_at=datetime(2026, 8, 27, 1, tzinfo=UTC),
        source="fixture_news",
        source_type="official_rss",
        url="https://example.invalid/private-source-url",
        canonical_url="https://example.invalid/private-source-url",
        summary="Revenue increased during the quarter.",
        content_hash="a" * 64,
        title_fingerprint="b" * 64,
        language="en",
        external_id="english-1",
    )
    chinese = NewsArticle(
        title="公司公告月營收成長並取得重大訂單",
        published_at=datetime(2026, 8, 28, 1, tzinfo=UTC),
        source="twse_material",
        source_type="official_announcement",
        url="https://example.invalid/twse-source-url",
        canonical_url="https://example.invalid/twse-source-url",
        summary="公開資訊觀測站重大訊息摘要",
        content_hash="c" * 64,
        title_fingerprint="d" * 64,
        language="zh-TW",
        external_id="chinese-1",
        source_metadata={"company_name": "範例公司", "clause": "31", "fact_date": "1150828"},
    )
    db_session.add_all([english, chinese])
    db_session.flush()
    db_session.add_all(
        [
            ArticleTicker(
                article_id=english.id,
                ticker="2330",
                relevance_score=Decimal("0.900"),
                match_method="company_alias_title",
            ),
            ArticleTicker(
                article_id=chinese.id,
                ticker="2330",
                relevance_score=Decimal("1.000"),
                match_method="official_company_code",
            ),
            SentimentResult(
                article_id=english.id,
                ticker="2330",
                model_version=FINBERT_VERSION,
                positive_prob=Decimal("0.70000000"),
                neutral_prob=Decimal("0.20000000"),
                negative_prob=Decimal("0.10000000"),
                sentiment_score=Decimal("0.60000000"),
                predicted_label="positive",
                input_hash=sentiment_input_hash(
                    build_sentiment_text(english.title, english.summary), FINBERT_VERSION
                ),
                scored_at=datetime(2026, 8, 28, 2, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/research/intelligence/2330?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_count"] == 2
    assert payload["retrieval_boundary"] == {
        "database_only": True,
        "external_api_called": False,
        "model_inference_performed": False,
        "llm_called": False,
        "full_article_content_returned": False,
    }
    chinese_result, english_result = payload["items"]
    assert chinese_result["sentiment"]["status"] == "ABSTAIN"
    assert chinese_result["sentiment"]["positive_probability"] is None
    assert chinese_result["event_intelligence"]["status"] == "SIGNAL"
    assert chinese_result["event_intelligence"]["sentiment_ground_truth"] is False
    assert english_result["sentiment"]["status"] == "SCORED"
    assert english_result["sentiment"]["model_version"] == FINBERT_VERSION
    assert english_result["sentiment"]["score"] == 0.6
    assert "url" not in english_result
    assert "private-source-url" not in response.text

    stored = db_session.get(SentimentResult, (english.id, "2330", FINBERT_VERSION))
    assert stored is not None
    stored.input_hash = "e" * 64
    db_session.commit()
    invalid_lineage = client.get("/api/v1/research/intelligence/2330?limit=10")
    assert invalid_lineage.status_code == 503
    assert invalid_lineage.json()["error"]["code"] == "service_unavailable"


def test_intelligence_endpoint_enforces_cutoff_limit_and_ticker_validation(
    client: TestClient,
    db_session: Session,
) -> None:
    article = NewsArticle(
        title="依規定補充說明相關資訊",
        published_at=datetime(2026, 8, 28, 1, tzinfo=UTC),
        source="twse_material",
        source_type="official_announcement",
        url="https://example.invalid/item",
        canonical_url="https://example.invalid/item",
        content_hash="f" * 64,
        title_fingerprint="1" * 64,
        language="zh-TW",
        external_id="cutoff-1",
    )
    db_session.add(article)
    db_session.flush()
    db_session.add(
        ArticleTicker(
            article_id=article.id,
            ticker="2330",
            relevance_score=Decimal("1.000"),
            match_method="official_company_code",
        )
    )
    db_session.commit()

    before = client.get(
        "/api/v1/research/intelligence/2330",
        params={"as_of_cutoff": "2026-08-27T23:59:59+00:00"},
    )
    excessive_limit = client.get("/api/v1/research/intelligence/2330?limit=51")
    invalid_ticker = client.get("/api/v1/research/intelligence/../../etc")

    assert before.status_code == 200
    assert before.json()["item_count"] == 0
    assert excessive_limit.status_code == 422
    assert invalid_ticker.status_code in {400, 404}
