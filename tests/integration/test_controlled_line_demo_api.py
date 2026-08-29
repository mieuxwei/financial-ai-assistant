from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.api.controlled_demo import get_f11b_authenticator
from backend.app.core.service_auth import (
    HmacServiceRequestAuthenticator,
    service_request_signature,
)
from backend.app.main import app

KEY_ID = "controlled-test-key"
SECRET = b"controlled-test-secret-not-for-production"
NOW = 1_800_000_000


def _headers(path: str, *, nonce: str = "controlled-nonce-0001") -> dict[str, str]:
    timestamp = str(NOW)
    body_sha256 = hashlib.sha256(b"").hexdigest()
    return {
        "X-F11B-Key-ID": KEY_ID,
        "X-F11B-Timestamp": timestamp,
        "X-F11B-Nonce": nonce,
        "X-F11B-Body-SHA256": body_sha256,
        "X-F11B-Signature": service_request_signature(
            SECRET,
            key_id=KEY_ID,
            timestamp=timestamp,
            nonce=nonce,
            method="GET",
            path=path,
            body_sha256=body_sha256,
        ),
    }


def _enable_test_auth() -> None:
    authenticator = HmacServiceRequestAuthenticator(
        KEY_ID, SECRET.decode(), now=lambda: NOW
    )
    app.dependency_overrides[get_f11b_authenticator] = lambda: authenticator


def test_controlled_stock_analysis_is_authenticated_fixture_only(
    client: TestClient,
) -> None:
    _enable_test_auth()
    path = "/api/v1/research/controlled-line-demo/STOCK_ANALYSIS/2330"

    response = client.get(path, headers=_headers(path))

    assert response.status_code == 200
    payload = response.json()
    assert payload["demo_label"] == "CONTROLLED RESEARCH DEMO"
    assert payload["ticker"] == "2330"
    assert payload["stock_analysis"]["risk_band"] == "HIGH"
    assert payload["stock_analysis"]["current_price"] is None
    assert payload["financial_intelligence"] is None
    assert payload["boundary"] == {
        "fixture_only": True,
        "read_only": True,
        "live_market_data": False,
        "external_api_called": False,
        "model_inference_performed": False,
        "portfolio_read": False,
        "portfolio_write": False,
    }


def test_controlled_intelligence_preserves_abstention_and_no_b5_signal(
    client: TestClient,
) -> None:
    _enable_test_auth()
    path = "/api/v1/research/controlled-line-demo/FINANCIAL_INTELLIGENCE/2330"

    response = client.get(path, headers=_headers(path, nonce="controlled-nonce-0002"))

    assert response.status_code == 200
    payload = response.json()
    intelligence = payload["financial_intelligence"]
    assert payload["stock_analysis"] is None
    assert intelligence["event_class"] == "REVENUE"
    assert intelligence["market_reaction_magnitude"] is None
    assert intelligence["direction_supported"] is False
    assert intelligence["chinese_sentiment_validated"] is False
    assert "ABSTAIN" not in response.text


def test_controlled_endpoint_fails_closed_for_missing_tampered_replayed_or_other_ticker(
    client: TestClient,
) -> None:
    _enable_test_auth()
    path = "/api/v1/research/controlled-line-demo/STOCK_ANALYSIS/2330"
    missing = client.get(path)
    tampered_headers = _headers(path, nonce="controlled-nonce-0003")
    tampered_headers["X-F11B-Signature"] = "0" * 64
    tampered = client.get(path, headers=tampered_headers)

    replay_headers = _headers(path, nonce="controlled-nonce-0004")
    first = client.get(path, headers=replay_headers)
    replay = client.get(path, headers=replay_headers)

    other_path = "/api/v1/research/controlled-line-demo/STOCK_ANALYSIS/2317"
    other = client.get(
        other_path, headers=_headers(other_path, nonce="controlled-nonce-0005")
    )

    assert missing.status_code == 401
    assert tampered.status_code == 401
    assert first.status_code == 200
    assert replay.status_code == 401
    assert other.status_code == 404
    assert all(
        response.json()["error"]["code"] in {"unauthorized", "not_found"}
        for response in (missing, tampered, replay, other)
    )


def test_controlled_fixture_remains_public_safe_static_asset() -> None:
    text = Path("demo/fixtures/controlled_dashboard_demo.v1.json").read_text(
        encoding="utf-8"
    )
    assert '"controlled_synthetic_data": true' in text
    assert '"actual_market_observation": false' in text
    assert '"private_or_user_data": false' in text
    assert "TWMD_API_KEY" not in text

    implementation = Path("backend/app/services/controlled_demo.py").read_text(
        encoding="utf-8"
    )
    for forbidden_runtime in (
        "predict_from_artifact",
        "FinancialIntelligenceService",
        "httpx",
        "requests.",
        "UrlFetchApp",
    ):
        assert forbidden_runtime not in implementation
