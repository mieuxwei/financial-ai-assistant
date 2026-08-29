from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request

from backend.app.core.config import get_settings
from backend.app.core.errors import ServiceUnavailableError
from backend.app.core.service_auth import HmacServiceRequestAuthenticator
from backend.app.schemas.controlled_demo import ControlledLineDemoResponse
from backend.app.services.controlled_demo import ControlledLineDemoService

router = APIRouter(prefix="/api/v1/research/controlled-line-demo", tags=["research"])
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@lru_cache
def get_f11b_authenticator() -> HmacServiceRequestAuthenticator:
    settings = get_settings()
    try:
        return HmacServiceRequestAuthenticator(
            settings.f11b_service_key_id, settings.f11b_service_secret
        )
    except ValueError as error:
        raise ServiceUnavailableError("controlled LINE service auth is unavailable") from error


@lru_cache
def get_controlled_line_demo_service() -> ControlledLineDemoService:
    configured = Path(get_settings().f11b_controlled_fixture_path)
    path = configured if configured.is_absolute() else REPOSITORY_ROOT / configured
    return ControlledLineDemoService(path)


async def require_f11b_service_request(
    request: Request,
    authenticator: Annotated[HmacServiceRequestAuthenticator, Depends(get_f11b_authenticator)],
    key_id: Annotated[str | None, Header(alias="X-F11B-Key-ID")] = None,
    timestamp: Annotated[str | None, Header(alias="X-F11B-Timestamp")] = None,
    nonce: Annotated[str | None, Header(alias="X-F11B-Nonce")] = None,
    body_sha256: Annotated[str | None, Header(alias="X-F11B-Body-SHA256")] = None,
    signature: Annotated[str | None, Header(alias="X-F11B-Signature")] = None,
) -> None:
    if None in {key_id, timestamp, nonce, body_sha256, signature}:
        from backend.app.core.errors import UnauthorizedError

        raise UnauthorizedError("missing service-request authentication")
    authenticator.verify(
        key_id=key_id,
        timestamp=timestamp,
        nonce=nonce,
        method=request.method,
        path=request.url.path,
        body=await request.body(),
        body_sha256=body_sha256,
        signature=signature,
    )


@router.get(
    "/{view}/{ticker}",
    response_model=ControlledLineDemoResponse,
    dependencies=[Depends(require_f11b_service_request)],
)
def get_controlled_line_demo(
    view: Literal["STOCK_ANALYSIS", "FINANCIAL_INTELLIGENCE"],
    ticker: str,
    service: Annotated[ControlledLineDemoService, Depends(get_controlled_line_demo_service)],
) -> ControlledLineDemoResponse:
    return service.get(view, ticker)
