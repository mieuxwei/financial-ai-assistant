from __future__ import annotations

import hmac
import re

from backend.app.core.errors import UnauthorizedError

DEMO_PRINCIPAL_PATTERN = re.compile(r"^dp_[0-9a-f]{64}$")


class DemoServiceAuthenticator:
    """Authenticate the dedicated Demo GAS service and validate its derived principal."""

    def __init__(self, token: str) -> None:
        if len(token) < 32:
            raise ValueError("public beta GAS service authentication is not configured")
        self._token = token

    def verify(self, authorization: str | None, principal_id: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("missing demo service authentication")
        supplied = authorization.removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, self._token):
            raise UnauthorizedError("invalid demo service authentication")
        if principal_id is None or DEMO_PRINCIPAL_PATTERN.fullmatch(principal_id) is None:
            raise UnauthorizedError("invalid demo principal")
        return principal_id
