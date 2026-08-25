from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import User


def headers(user: User) -> dict[str, str]:
    return {"X-User-ID": user.id}


def holding_payload(ticker: str, name: str = "Example") -> dict[str, object]:
    return {
        "ticker": ticker,
        "name": name,
        "quantity": "1000",
        "cost_basis": "100.5",
        "take_profit_pct": "20",
        "stop_loss_pct": "-10",
    }


def test_users_cannot_read_or_write_each_others_portfolios(
    client: TestClient,
    users: tuple[User, User],
) -> None:
    user_a, user_b = users

    read_response = client.get(f"/users/{user_b.id}/portfolio", headers=headers(user_a))
    write_response = client.post(
        f"/users/{user_b.id}/holdings",
        headers=headers(user_a),
        json=holding_payload("2330"),
    )

    assert read_response.status_code == 403
    assert write_response.status_code == 403
    own_response = client.get(f"/users/{user_b.id}/portfolio", headers=headers(user_b))
    assert own_response.status_code == 200
    assert own_response.json()["holdings"] == []


def test_create_and_update_holding(
    client: TestClient,
    users: tuple[User, User],
) -> None:
    user, _ = users
    create_response = client.post(
        f"/users/{user.id}/holdings",
        headers=headers(user),
        json=holding_payload("2330.tw", "TSMC"),
    )
    assert create_response.status_code == 201
    holding = create_response.json()
    assert holding["ticker"] == "2330"

    update_response = client.patch(
        f"/users/{user.id}/holdings/{holding['id']}",
        headers=headers(user),
        json={"quantity": "2000"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity"] == "2000.0000"


def test_sync_preview_and_confirm_are_idempotent(
    client: TestClient,
    users: tuple[User, User],
) -> None:
    user, _ = users
    client.post(
        f"/users/{user.id}/holdings",
        headers=headers(user),
        json=holding_payload("0050", "ETF"),
    )
    preview_response = client.post(
        f"/users/{user.id}/portfolio-sync/preview",
        headers=headers(user),
        json={"holdings": [holding_payload("2330", "TSMC")]},
    )
    assert preview_response.status_code == 201
    preview = preview_response.json()
    assert (preview["additions"], preview["updates"], preview["removals"]) == (1, 0, 1)

    confirm_url = f"/users/{user.id}/portfolio-sync/{preview['operation_id']}/confirm"
    first_confirm = client.post(confirm_url, headers=headers(user))
    second_confirm = client.post(confirm_url, headers=headers(user))

    assert first_confirm.status_code == 200
    assert first_confirm.json()["applied"] is True
    assert second_confirm.status_code == 200
    assert second_confirm.json()["applied"] is False
    assert [item["ticker"] for item in second_confirm.json()["portfolio"]["holdings"]] == [
        "2330"
    ]


def test_invalid_sync_does_not_change_existing_holdings(
    client: TestClient,
    users: tuple[User, User],
    db_session: Session,
) -> None:
    user, _ = users
    client.post(
        f"/users/{user.id}/holdings",
        headers=headers(user),
        json=holding_payload("0050", "ETF"),
    )
    invalid_payload = holding_payload("2330", "=UNSAFE")
    response = client.post(
        f"/users/{user.id}/portfolio-sync/preview",
        headers=headers(user),
        json={"holdings": [invalid_payload]},
    )

    assert response.status_code == 422
    db_session.expire_all()
    portfolio_response = client.get(f"/users/{user.id}/portfolio", headers=headers(user))
    assert [item["ticker"] for item in portfolio_response.json()["holdings"]] == ["0050"]


def test_sync_database_failure_rolls_back_all_changes(
    client: TestClient,
    users: tuple[User, User],
    db_session: Session,
    monkeypatch,
) -> None:
    user, _ = users
    client.post(
        f"/users/{user.id}/holdings",
        headers=headers(user),
        json=holding_payload("0050", "ETF"),
    )
    preview = client.post(
        f"/users/{user.id}/portfolio-sync/preview",
        headers=headers(user),
        json={"holdings": [holding_payload("2330", "TSMC")]},
    ).json()
    original_commit = db_session.commit

    def fail_commit() -> None:
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    confirm_url = f"/users/{user.id}/portfolio-sync/{preview['operation_id']}/confirm"
    response = client.post(confirm_url, headers=headers(user))
    monkeypatch.setattr(db_session, "commit", original_commit)

    assert response.status_code == 409
    db_session.expire_all()
    portfolio_response = client.get(f"/users/{user.id}/portfolio", headers=headers(user))
    assert [item["ticker"] for item in portfolio_response.json()["holdings"]] == ["0050"]
