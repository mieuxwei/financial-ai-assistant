from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from backend.app.schemas.research import FinancialIntelligenceResponse
from demo.client import DashboardApiClient, DashboardApiError
from demo.contracts import load_controlled_fixture, load_dashboard_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/dashboard_demo.v1.json"


def _fixture():
    config = load_dashboard_config(CONFIG_PATH)
    return load_controlled_fixture(ROOT / config.fixture_path)


@pytest.mark.parametrize(
    "url",
    (
        "https://127.0.0.1:8000",
        "http://example.com:8000",
        "http://user:password@localhost:8000",
        "http://localhost:8000/api",
        "http://localhost:8000?token=secret",
        "http://localhost",
    ),
)
def test_dashboard_client_rejects_non_loopback_or_ambiguous_origins(url: str) -> None:
    with pytest.raises(ValueError, match="loopback origin|explicit local port"):
        DashboardApiClient(url)


def test_dashboard_client_validates_f10_responses() -> None:
    fixture = _fixture()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/predict"):
            return httpx.Response(200, json=fixture.prediction_response.model_dump(mode="json"))
        response = FinancialIntelligenceResponse(
            schema_version="financial-intelligence-response-v1",
            ticker="2330",
            as_of_cutoff=None,
            item_count=len(fixture.intelligence_items),
            items=fixture.intelligence_items,
            intelligence_version=fixture.intelligence_version,
            config_sha256=fixture.intelligence_items[0].lineage.config_sha256,
            retrieval_boundary={
                "database_only": True,
                "external_api_called": False,
                "model_inference_performed": False,
                "llm_called": False,
                "full_article_content_returned": False,
            },
            disclaimer="Research intelligence only; not investment advice.",
        )
        return httpx.Response(200, json=response.model_dump(mode="json"))

    client = DashboardApiClient(
        "http://127.0.0.1:8000", transport=httpx.MockTransport(handler)
    )

    prediction = client.predict(fixture.prediction_request)
    intelligence = client.intelligence("2330")

    assert prediction == fixture.prediction_response
    assert intelligence.items == fixture.intelligence_items
    assert intelligence.retrieval_boundary.external_api_called is False


def test_dashboard_client_does_not_leak_error_response_body() -> None:
    secret_marker = "SHOULD_NOT_APPEAR"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=json.dumps({"detail": secret_marker}))

    client = DashboardApiClient(
        "http://localhost:8000", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(DashboardApiError) as captured:
        client.intelligence("2330")

    assert secret_marker not in str(captured.value)
