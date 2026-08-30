from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.demo_liff import (
    get_demo_identity_secret,
    get_liff_session_codec,
    get_liff_verifier,
)
from backend.app.core.liff_auth import LiffSessionCodec, derive_demo_principal
from backend.app.main import app
from backend.app.models import DemoPrincipal

IDENTITY_SECRET = "identity-secret-for-liff-integration-tests-32bytes"
SESSION_SECRET = "session-secret-for-liff-integration-tests-32bytes"
RAW_USER_A = f"U{'1a' * 16}"
RAW_USER_B = f"U{'2b' * 16}"


class FakeLineVerifier:
    def __init__(self) -> None:
        self.subject = RAW_USER_A

    async def verify(self, id_token: str) -> str:
        assert id_token == "synthetic-line-id-token"
        return self.subject


@pytest.fixture(autouse=True)
def liff_auth_override() -> Iterator[FakeLineVerifier]:
    verifier = FakeLineVerifier()
    app.dependency_overrides[get_liff_verifier] = lambda: verifier
    app.dependency_overrides[get_liff_session_codec] = lambda: LiffSessionCodec(SESSION_SECRET)
    app.dependency_overrides[get_demo_identity_secret] = lambda: IDENTITY_SECRET
    yield verifier
    app.dependency_overrides.pop(get_liff_verifier, None)
    app.dependency_overrides.pop(get_liff_session_codec, None)
    app.dependency_overrides.pop(get_demo_identity_secret, None)


def session_headers(
    client: TestClient, verifier: FakeLineVerifier, raw_user: str
) -> dict[str, str]:
    verifier.subject = raw_user
    response = client.post(
        "/api/v1/demo/liff/session",
        json={"id_token": "synthetic-line-id-token"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def accept_disclosure(client: TestClient, headers: dict[str, str], suffix: str) -> None:
    response = client.post(
        "/api/v1/demo/liff/disclosure",
        headers={**headers, "Idempotency-Key": f"liff-disclosure-{suffix}-0001"},
    )
    assert response.status_code == 200, response.text


def test_liff_batch_replaces_multiple_holdings_atomically(
    client: TestClient, liff_auth_override: FakeLineVerifier
) -> None:
    headers = session_headers(client, liff_auth_override, RAW_USER_A)
    accept_disclosure(client, headers, "a")
    bootstrap = client.get("/api/v1/demo/liff/bootstrap", headers=headers).json()

    response = client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers, "Idempotency-Key": "liff-batch-create-0001"},
        json={
            "expected_portfolio_version": bootstrap["portfolio"]["portfolio_version"],
            "holdings": [
                {"ticker": "0050", "shares": "10", "average_cost": "200"},
                {"ticker": "2317", "shares": "20", "average_cost": "180"},
                {"ticker": "2330", "shares": "30", "average_cost": "900"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    portfolio = response.json()["portfolio"]
    assert [item["ticker"] for item in portfolio["holdings"]] == ["0050", "2317", "2330"]

    existing_2330 = next(item for item in portfolio["holdings"] if item["ticker"] == "2330")
    replaced = client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers, "Idempotency-Key": "liff-batch-replace-0002"},
        json={
            "expected_portfolio_version": portfolio["portfolio_version"],
            "holdings": [
                {
                    "ticker": "2330",
                    "shares": "35",
                    "average_cost": "880",
                    "holding_id": existing_2330["id"],
                    "version": existing_2330["version"],
                },
                {"ticker": "2454", "shares": "40", "average_cost": "1200"},
            ],
        },
    )
    assert replaced.status_code == 200, replaced.text
    assert [item["ticker"] for item in replaced.json()["portfolio"]["holdings"]] == [
        "2330",
        "2454",
    ]


def test_invalid_batch_is_all_or_nothing_and_stale_version_conflicts(
    client: TestClient, liff_auth_override: FakeLineVerifier
) -> None:
    headers = session_headers(client, liff_auth_override, RAW_USER_A)
    accept_disclosure(client, headers, "a")
    initial = client.get("/api/v1/demo/liff/bootstrap", headers=headers).json()["portfolio"]
    created = client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers, "Idempotency-Key": "liff-batch-valid-0001"},
        json={
            "expected_portfolio_version": initial["portfolio_version"],
            "holdings": [{"ticker": "2330", "shares": "10", "average_cost": "900"}],
        },
    ).json()["portfolio"]

    duplicate = client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers, "Idempotency-Key": "liff-batch-invalid-0002"},
        json={
            "expected_portfolio_version": created["portfolio_version"],
            "holdings": [
                {"ticker": "0050", "shares": "10", "average_cost": "200"},
                {"ticker": "0050", "shares": "20", "average_cost": "210"},
            ],
        },
    )
    assert duplicate.status_code == 422
    after = client.get("/api/v1/demo/liff/bootstrap", headers=headers).json()["portfolio"]
    assert [item["ticker"] for item in after["holdings"]] == ["2330"]

    stale = client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers, "Idempotency-Key": "liff-batch-stale-0003"},
        json={"expected_portfolio_version": "0" * 64, "holdings": []},
    )
    assert stale.status_code == 409


def test_liff_identity_is_isolated_and_raw_line_id_is_not_persisted(
    client: TestClient,
    db_session: Session,
    liff_auth_override: FakeLineVerifier,
) -> None:
    headers_a = session_headers(client, liff_auth_override, RAW_USER_A)
    headers_b = session_headers(client, liff_auth_override, RAW_USER_B)
    accept_disclosure(client, headers_a, "a")
    bootstrap_a = client.get("/api/v1/demo/liff/bootstrap", headers=headers_a).json()
    client.put(
        "/api/v1/demo/liff/portfolio",
        headers={**headers_a, "Idempotency-Key": "liff-user-a-write-0001"},
        json={
            "expected_portfolio_version": bootstrap_a["portfolio"]["portfolio_version"],
            "holdings": [{"ticker": "2330", "shares": "10", "average_cost": "900"}],
        },
    )
    bootstrap_b = client.get("/api/v1/demo/liff/bootstrap", headers=headers_b).json()
    assert bootstrap_b["portfolio"]["holdings"] == []

    principal_ids = list(db_session.scalars(select(DemoPrincipal.id)))
    assert derive_demo_principal(RAW_USER_A, IDENTITY_SECRET) in principal_ids
    assert RAW_USER_A not in principal_ids and RAW_USER_B not in principal_ids


def test_liff_page_is_controlled_and_contains_no_live_or_direction_claim(
    client: TestClient,
) -> None:
    response = client.get("/demo/liff/portfolio")
    assert response.status_code == 200
    assert "CONTROLLED RESEARCH DEMO" in response.text
    assert "不取得即時價格" in response.text
    assert "不預測股價上漲或下跌" in response.text
    assert "買進" not in response.text and "賣出" not in response.text
