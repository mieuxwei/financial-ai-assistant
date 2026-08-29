import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.controlled_demo import router as controlled_demo_router
from backend.app.api.demo_sandbox import router as demo_sandbox_router
from backend.app.api.portfolios import router as portfolio_router
from backend.app.api.research import router as research_router
from backend.app.core.config import get_settings
from backend.app.core.errors import AppError
from backend.app.core.logging import configure_logging
from backend.app.schemas.health import HealthResponse

settings = get_settings()
configure_logging(settings.app_env)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(title=settings.service_name)
    application.include_router(portfolio_router)
    application.include_router(research_router)
    application.include_router(controlled_demo_router)
    application.include_router(demo_sandbox_router)

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "request validation failed",
                    "details": details,
                }
            },
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("unhandled application error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "internal server error"}},
        )

    return application


app = create_app()


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report whether the API process is available."""
    return HealthResponse(status="ok", service=settings.service_name)
