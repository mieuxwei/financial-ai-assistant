from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections.abc import Callable

from backend.app.core.errors import UnauthorizedError


class HmacServiceRequestAuthenticator:
    """Verify the frozen F11B service-request signature and reject nonce replay."""

    def __init__(
        self,
        key_id: str,
        secret: str,
        *,
        maximum_clock_skew_seconds: int = 300,
        now: Callable[[], float] = time.time,
    ) -> None:
        if not key_id or len(secret) < 32:
            raise ValueError("F11B service authentication is not configured")
        self.key_id = key_id
        self.secret = secret.encode()
        self.maximum_clock_skew_seconds = maximum_clock_skew_seconds
        self.now = now
        self._nonces: dict[str, int] = {}
        self._lock = threading.Lock()

    def verify(
        self,
        *,
        key_id: str,
        timestamp: str,
        nonce: str,
        method: str,
        path: str,
        body: bytes,
        body_sha256: str,
        signature: str,
    ) -> None:
        try:
            timestamp_value = int(timestamp)
        except ValueError as error:
            raise UnauthorizedError("invalid service-request timestamp") from error
        now = int(self.now())
        if abs(now - timestamp_value) > self.maximum_clock_skew_seconds:
            raise UnauthorizedError("service-request timestamp is outside the allowed window")
        if key_id != self.key_id or not _valid_token(nonce, 16, 128):
            raise UnauthorizedError("invalid service-request identity")

        actual_body_sha256 = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(actual_body_sha256, body_sha256):
            raise UnauthorizedError("service-request body hash mismatch")
        expected = service_request_signature(
            self.secret,
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            path=path,
            body_sha256=body_sha256,
        )
        if not hmac.compare_digest(expected, signature):
            raise UnauthorizedError("invalid service-request signature")

        with self._lock:
            self._nonces = {
                value: seen_at
                for value, seen_at in self._nonces.items()
                if now - seen_at <= self.maximum_clock_skew_seconds
            }
            if nonce in self._nonces:
                raise UnauthorizedError("service-request nonce has already been used")
            self._nonces[nonce] = now


def service_request_signature(
    secret: bytes,
    *,
    key_id: str,
    timestamp: str,
    nonce: str,
    method: str,
    path: str,
    body_sha256: str,
) -> str:
    canonical = "\n".join(
        (key_id, timestamp, nonce, method.upper(), path, body_sha256)
    )
    return hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest()


def _valid_token(value: str, minimum: int, maximum: int) -> bool:
    return minimum <= len(value) <= maximum and all(
        character.isalnum() or character in "-_" for character in value
    )
