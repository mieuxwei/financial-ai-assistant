from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import HTMLResponse

from backend.app.api.demo_sandbox import DemoService
from backend.app.core.config import get_settings
from backend.app.core.errors import ServiceUnavailableError
from backend.app.core.liff_auth import (
    LiffSessionCodec,
    LineIdTokenVerifier,
    derive_demo_principal,
)
from backend.app.schemas.demo_sandbox import (
    DemoLiffBootstrapResponse,
    DemoLiffSessionRequest,
    DemoLiffSessionResponse,
    DemoMutationResponse,
    DemoPortfolioBatchResponse,
    DemoPortfolioBatchWrite,
)

router = APIRouter(prefix="/api/v1/demo/liff", tags=["line-public-beta-liff"])
page_router = APIRouter(tags=["line-public-beta-liff"])
STATIC_ROOT = Path(__file__).resolve().parents[1] / "static" / "demo_liff"


@lru_cache
def get_liff_verifier() -> LineIdTokenVerifier:
    try:
        return LineIdTokenVerifier(get_settings().line_demo_liff_channel_id)
    except ValueError as error:
        raise ServiceUnavailableError("LIFF identity verification is unavailable") from error


@lru_cache
def get_liff_session_codec() -> LiffSessionCodec:
    settings = get_settings()
    try:
        return LiffSessionCodec(
            settings.demo_liff_session_secret,
            lifetime_minutes=settings.demo_liff_session_minutes,
        )
    except ValueError as error:
        raise ServiceUnavailableError("LIFF session authentication is unavailable") from error


def get_demo_identity_secret() -> str:
    value = get_settings().demo_identity_secret
    if len(value) < 32:
        raise ServiceUnavailableError("LIFF identity derivation is unavailable")
    return value


def require_liff_principal(
    codec: Annotated[LiffSessionCodec, Depends(get_liff_session_codec)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    return codec.verify(authorization)


LiffPrincipal = Annotated[str, Depends(require_liff_principal)]


@router.post("/session", response_model=DemoLiffSessionResponse)
async def create_liff_session(
    values: DemoLiffSessionRequest,
    verifier: Annotated[LineIdTokenVerifier, Depends(get_liff_verifier)],
    codec: Annotated[LiffSessionCodec, Depends(get_liff_session_codec)],
    identity_secret: Annotated[str, Depends(get_demo_identity_secret)],
) -> DemoLiffSessionResponse:
    raw_line_user_id = await verifier.verify(values.id_token)
    principal = derive_demo_principal(raw_line_user_id, identity_secret)
    session = codec.issue(principal)
    return DemoLiffSessionResponse(
        access_token=session.access_token,
        expires_at=session.expires_at,
    )


@router.get("/bootstrap", response_model=DemoLiffBootstrapResponse)
def get_liff_bootstrap(principal: LiffPrincipal, service: DemoService) -> DemoLiffBootstrapResponse:
    return service.liff_bootstrap(principal)


@router.post("/disclosure", response_model=DemoMutationResponse)
def accept_liff_disclosure(
    principal: LiffPrincipal,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> DemoMutationResponse:
    return service.accept_disclosure(principal, idempotency_key)


@router.put(
    "/portfolio",
    response_model=DemoPortfolioBatchResponse,
    status_code=status.HTTP_200_OK,
)
def replace_liff_portfolio(
    values: DemoPortfolioBatchWrite,
    principal: LiffPrincipal,
    service: DemoService,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> DemoPortfolioBatchResponse:
    return service.replace_portfolio(principal, idempotency_key, values)


@page_router.get("/demo/liff/portfolio", response_class=HTMLResponse, include_in_schema=False)
def demo_liff_portfolio_page() -> HTMLResponse:
    template = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    public_config = json.dumps(
        {"liffId": get_settings().line_demo_liff_id},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return HTMLResponse(
        template.replace("__PUBLIC_LIFF_CONFIG__", public_config),
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        },
    )
