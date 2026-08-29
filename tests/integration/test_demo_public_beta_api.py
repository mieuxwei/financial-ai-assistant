from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.api.demo_sandbox import get_demo_authenticator
from backend.app.core.demo_auth import DemoServiceAuthenticator
from backend.app.main import app

TEST_TOKEN = "demo-gas-service-token-for-tests-only-32bytes"
PRINCIPAL_A = f"dp_{'a' * 64}"
PRINCIPAL_B = f"dp_{'b' * 64}"


@pytest.fixture(autouse=True)
def demo_auth_override() -> Iterator[None]:
    app.dependency_overrides[get_demo_authenticator] = lambda: DemoServiceAuthenticator(TEST_TOKEN)
    yield
    app.dependency_overrides.pop(get_demo_authenticator, None)


def headers(principal: str, *, key: str | None = None, token: str = TEST_TOKEN) -> dict[str, str]:
    result = {
        "Authorization": f"Bearer {token}",
        "X-Demo-Principal-ID": principal,
    }
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def accept_disclosure(client: TestClient, principal: str, suffix: str = "a") -> None:
    response = client.post(
        "/api/v1/demo/me/disclosure",
        headers=headers(principal, key=f"evt-disclosure-{suffix}-0001"),
    )
    assert response.status_code == 200


def create_holding(
    client: TestClient,
    principal: str,
    ticker: str = "2330",
    *,
    key: str = "evt-create-holding-0001",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/demo/portfolio/holdings",
        headers=headers(principal, key=key),
        json={"ticker": ticker, "shares": "100", "average_cost": "820"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_backend_rejects_missing_invalid_auth_and_untrusted_principal(client: TestClient) -> None:
    assert client.get("/api/v1/demo/portfolio").status_code == 401
    assert client.get(
        "/api/v1/demo/portfolio", headers=headers(PRINCIPAL_A, token="x" * 32)
    ).status_code == 401
    invalid_principal_headers = headers(PRINCIPAL_A)
    invalid_principal_headers["X-Demo-Principal-ID"] = "raw-line-user-id"
    assert client.get(
        "/api/v1/demo/portfolio", headers=invalid_principal_headers
    ).status_code == 401


def test_duplicate_event_id_does_not_duplicate_holding(client: TestClient) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    key = "webhook-event-create-0001"
    first = create_holding(client, PRINCIPAL_A, key=key)
    second = create_holding(client, PRINCIPAL_A, key=key)

    assert first["holding"]["id"] == second["holding"]["id"]
    portfolio = client.get("/api/v1/demo/portfolio", headers=headers(PRINCIPAL_A)).json()
    assert len(portfolio["holdings"]) == 1


def test_user_isolation_blocks_read_update_and_delete_by_holding_id(client: TestClient) -> None:
    accept_disclosure(client, PRINCIPAL_A, "a")
    accept_disclosure(client, PRINCIPAL_B, "b")
    holding = create_holding(client, PRINCIPAL_B, key="evt-user-b-create-0001")["holding"]

    own_a = client.get("/api/v1/demo/portfolio", headers=headers(PRINCIPAL_A)).json()
    own_b = client.get("/api/v1/demo/portfolio", headers=headers(PRINCIPAL_B)).json()
    assert own_a["holdings"] == []
    assert len(own_b["holdings"]) == 1

    update = client.patch(
        f"/api/v1/demo/portfolio/holdings/{holding['id']}",
        headers=headers(PRINCIPAL_A, key="evt-cross-update-0001"),
        json={"shares": "200", "average_cost": "800", "version": holding["version"]},
    )
    delete = client.delete(
        f"/api/v1/demo/portfolio/holdings/{holding['id']}?version={holding['version']}",
        headers=headers(PRINCIPAL_A, key="evt-cross-delete-0001"),
    )
    assert update.status_code == 404
    assert delete.status_code == 404


def test_update_and_delete_are_versioned_confirmed_mutations(client: TestClient) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    holding = create_holding(client, PRINCIPAL_A)["holding"]
    update = client.patch(
        f"/api/v1/demo/portfolio/holdings/{holding['id']}",
        headers=headers(PRINCIPAL_A, key="evt-update-holding-0001"),
        json={"shares": "250", "average_cost": "810", "version": holding["version"]},
    )
    assert update.status_code == 200
    updated = update.json()["holding"]
    assert Decimal(updated["shares"]) == Decimal("250")
    assert updated["version"] == 2

    stale = client.patch(
        f"/api/v1/demo/portfolio/holdings/{holding['id']}",
        headers=headers(PRINCIPAL_A, key="evt-update-holding-0002"),
        json={"shares": "300", "average_cost": "810", "version": 1},
    )
    assert stale.status_code == 409

    deleted = client.delete(
        f"/api/v1/demo/portfolio/holdings/{holding['id']}?version=2",
        headers=headers(PRINCIPAL_A, key="evt-delete-holding-0001"),
    )
    assert deleted.status_code == 200
    assert client.get(
        "/api/v1/demo/portfolio", headers=headers(PRINCIPAL_A)
    ).json()["holdings"] == []


def test_max_five_holdings_and_frozen_universe_are_enforced(client: TestClient) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    for index, ticker in enumerate(("0050", "1301", "1303", "2308", "2317"), start=1):
        create_holding(
            client,
            PRINCIPAL_A,
            ticker,
            key=f"evt-create-max-{index:04d}",
        )
    sixth = client.post(
        "/api/v1/demo/portfolio/holdings",
        headers=headers(PRINCIPAL_A, key="evt-create-max-0006"),
        json={"ticker": "2330", "shares": "100", "average_cost": "820"},
    )
    assert sixth.status_code == 409

    accept_disclosure(client, PRINCIPAL_B, "b")
    invalid = client.post(
        "/api/v1/demo/portfolio/holdings",
        headers=headers(PRINCIPAL_B, key="evt-invalid-ticker-0001"),
        json={"ticker": "9999", "shares": "100", "average_cost": "10"},
    )
    assert invalid.status_code == 400


@pytest.mark.parametrize(
    ("shares", "cost"),
    [("-1", "10"), ("NaN", "10"), ("Infinity", "10"), ("1", "-2"), ("1", "Infinity")],
)
def test_non_finite_and_non_positive_values_are_rejected(
    client: TestClient, shares: str, cost: str
) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    response = client.post(
        "/api/v1/demo/portfolio/holdings",
        headers=headers(PRINCIPAL_A, key=f"evt-invalid-number-{shares}-{cost}"[:128]),
        json={"ticker": "2330", "shares": shares, "average_cost": cost},
    )
    assert response.status_code == 422


def test_disclosure_is_required_before_first_write(client: TestClient) -> None:
    response = client.post(
        "/api/v1/demo/portfolio/holdings",
        headers=headers(PRINCIPAL_A, key="evt-no-disclosure-0001"),
        json={"ticker": "2330", "shares": "100", "average_cost": "820"},
    )
    assert response.status_code == 409


def test_delete_my_data_removes_holdings_and_preferences(client: TestClient) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    create_holding(client, PRINCIPAL_A)
    deleted = client.delete("/api/v1/demo/me", headers=headers(PRINCIPAL_A))
    repeated = client.delete("/api/v1/demo/me", headers=headers(PRINCIPAL_A))
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
    assert repeated.status_code == 200 and repeated.json()["deleted"] is False
    recreated = client.get("/api/v1/demo/me", headers=headers(PRINCIPAL_A)).json()
    assert recreated["disclosure_accepted"] is False
    assert client.get(
        "/api/v1/demo/portfolio", headers=headers(PRINCIPAL_A)
    ).json()["holdings"] == []


def test_portfolio_health_is_controlled_and_never_claims_current_price_or_direction(
    client: TestClient,
) -> None:
    accept_disclosure(client, PRINCIPAL_A)
    create_holding(client, PRINCIPAL_A)
    health = client.post(
        "/api/v1/demo/portfolio/health", headers=headers(PRINCIPAL_A)
    ).json()
    assert health["demo_label"] == "CONTROLLED RESEARCH SIGNAL"
    item = health["items"][0]
    assert item["reference_price"] is None
    assert item["roi"] is None
    assert item["research"]["current_market_inference"] is False
    assert item["research"]["direction"] is None
    assert item["intelligence"]["chinese_sentiment"] is None
    assert "尚未通過獨立驗證" in item["intelligence"]["chinese_sentiment_message"]


def test_non_fixture_ticker_abstains_instead_of_fabricating_signal(client: TestClient) -> None:
    response = client.get(
        "/api/v1/demo/research/stock-analysis/2317", headers=headers(PRINCIPAL_A)
    )
    assert response.status_code == 200
    research = response.json()["research"]
    assert research["status"] == "UNAVAILABLE_FOR_CONTROLLED_FIXTURE"
    assert research["score"] is None
    assert research["historical_percentile"] is None
    assert research["communication_band"] is None
