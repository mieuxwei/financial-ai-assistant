from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.app.core.demo_auth import DEMO_PRINCIPAL_PATTERN
from backend.app.core.errors import ServiceUnavailableError, UnauthorizedError

LINE_ID_TOKEN_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
SESSION_AUDIENCE = "financial-ai-demo-liff"
RAW_LINE_USER_PATTERN = re.compile(r"^U[0-9a-fA-F]{32}$")


def derive_demo_principal(raw_line_user_id: str, identity_secret: str) -> str:
    """Match the Security Edge principal derivation without persisting the LINE user ID."""
    if not RAW_LINE_USER_PATTERN.fullmatch(raw_line_user_id):
        raise UnauthorizedError("LINE identity is invalid")
    if len(identity_secret) < 32:
        raise ServiceUnavailableError("LIFF identity derivation is unavailable")
    digest = hmac.new(
        identity_secret.encode("utf-8"),
        raw_line_user_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"dp_{digest}"


class LineIdTokenVerifier:
    """Verify a raw LIFF ID token with LINE; never trust decoded browser profile data."""

    def __init__(self, channel_id: str, *, timeout_seconds: float = 5.0) -> None:
        if not channel_id.isdigit():
            raise ValueError("LIFF channel ID is not configured")
        self.channel_id = channel_id
        self.timeout_seconds = timeout_seconds

    async def verify(self, id_token: str) -> str:
        if not id_token or len(id_token) > 4096:
            raise UnauthorizedError("LIFF ID token is invalid")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    LINE_ID_TOKEN_VERIFY_URL,
                    data={"id_token": id_token, "client_id": self.channel_id},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as error:
            raise ServiceUnavailableError("LINE identity verification is unavailable") from error
        if response.status_code != 200:
            raise UnauthorizedError("LIFF ID token verification failed")
        payload = response.json()
        if str(payload.get("aud")) != self.channel_id:
            raise UnauthorizedError("LIFF ID token audience is invalid")
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise UnauthorizedError("LIFF ID token subject is missing")
        return subject


@dataclass(frozen=True)
class LiffSession:
    access_token: str
    expires_at: datetime


class LiffSessionCodec:
    """Issue short-lived, stateless HMAC sessions for the LIFF portfolio editor."""

    def __init__(self, secret: str, *, lifetime_minutes: int = 15) -> None:
        if len(secret) < 32:
            raise ValueError("LIFF session secret is not configured")
        if not 1 <= lifetime_minutes <= 60:
            raise ValueError("LIFF session lifetime must be between 1 and 60 minutes")
        self._secret = secret.encode("utf-8")
        self._lifetime = timedelta(minutes=lifetime_minutes)

    def issue(self, principal_id: str, *, now: datetime | None = None) -> LiffSession:
        if DEMO_PRINCIPAL_PATTERN.fullmatch(principal_id) is None:
            raise UnauthorizedError("demo principal is invalid")
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + self._lifetime
        payload = {
            "v": 1,
            "aud": SESSION_AUDIENCE,
            "pid": principal_id,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        encoded = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _base64url(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return LiffSession(access_token=f"{encoded}.{signature}", expires_at=expires_at)

    def verify(self, authorization: str | None, *, now: datetime | None = None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("missing LIFF session authentication")
        token = authorization.removeprefix("Bearer ")
        try:
            encoded, supplied_signature = token.split(".", 1)
            expected = _base64url(
                hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(supplied_signature, expected):
                raise UnauthorizedError("invalid LIFF session authentication")
            payload: dict[str, Any] = json.loads(_base64url_decode(encoded))
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            raise UnauthorizedError("invalid LIFF session authentication") from error
        current = now or datetime.now(UTC)
        if payload.get("v") != 1 or payload.get("aud") != SESSION_AUDIENCE:
            raise UnauthorizedError("invalid LIFF session authentication")
        if not isinstance(payload.get("exp"), int) or int(current.timestamp()) >= payload["exp"]:
            raise UnauthorizedError("LIFF session has expired")
        principal = payload.get("pid")
        if not isinstance(principal, str) or DEMO_PRINCIPAL_PATTERN.fullmatch(principal) is None:
            raise UnauthorizedError("invalid LIFF session principal")
        return principal


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
