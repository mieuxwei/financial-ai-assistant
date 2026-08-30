from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.core.errors import UnauthorizedError
from backend.app.core.liff_auth import LiffSessionCodec, derive_demo_principal

IDENTITY_SECRET = "identity-secret-for-liff-unit-tests-32bytes"
SESSION_SECRET = "session-secret-for-liff-unit-tests-32bytes"
RAW_LINE_USER_ID = f"U{'1a' * 16}"


def test_principal_derivation_is_stable_and_does_not_embed_line_user_id() -> None:
    first = derive_demo_principal(RAW_LINE_USER_ID, IDENTITY_SECRET)
    second = derive_demo_principal(RAW_LINE_USER_ID, IDENTITY_SECRET)

    assert first == second
    assert first.startswith("dp_") and len(first) == 67
    assert RAW_LINE_USER_ID not in first


def test_liff_session_rejects_tampering_and_expiry() -> None:
    codec = LiffSessionCodec(SESSION_SECRET, lifetime_minutes=15)
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    principal = derive_demo_principal(RAW_LINE_USER_ID, IDENTITY_SECRET)
    session = codec.issue(principal, now=now)

    assert codec.verify(f"Bearer {session.access_token}", now=now) == principal
    with pytest.raises(UnauthorizedError):
        codec.verify(f"Bearer {session.access_token[:-1]}x", now=now)
    with pytest.raises(UnauthorizedError):
        codec.verify(f"Bearer {session.access_token}", now=now + timedelta(minutes=15))


@pytest.mark.parametrize("raw_user_id", ["raw-user", "", "U1234"])
def test_invalid_raw_line_user_id_is_rejected(raw_user_id: str) -> None:
    with pytest.raises(UnauthorizedError):
        derive_demo_principal(raw_user_id, IDENTITY_SECRET)
