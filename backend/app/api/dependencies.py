from typing import Annotated

from fastapi import Header

from backend.app.core.errors import ForbiddenError


def require_user_access(
    user_id: str,
    x_user_id: Annotated[str, Header(alias="X-User-ID")],
) -> str:
    """Transitional identity boundary until M10 verifies LINE signatures directly."""
    if x_user_id != user_id:
        raise ForbiddenError("requested user does not match the authenticated user context")
    return user_id
