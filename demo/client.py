from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from backend.app.schemas.research import (
    FinancialIntelligenceResponse,
    VolatilitySurprisePredictionRequest,
    VolatilitySurprisePredictionResponse,
)

PREDICTION_PATH = "/api/v1/research/volatility-surprise/predict"
INTELLIGENCE_PATH = "/api/v1/research/intelligence/{ticker}"


class DashboardApiError(RuntimeError):
    """Safe user-facing local API error without response-body leakage."""


class DashboardApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "::1"),
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = _validate_loopback_url(base_url, allowed_hosts)
        self.timeout = httpx.Timeout(timeout_seconds)
        self.transport = transport

    def predict(
        self, request: VolatilitySurprisePredictionRequest
    ) -> VolatilitySurprisePredictionResponse:
        payload = self._request(
            "POST", PREDICTION_PATH, json=request.model_dump(mode="json")
        )
        try:
            return VolatilitySurprisePredictionResponse.model_validate(payload)
        except ValueError as error:
            raise DashboardApiError("本機 prediction API 回應不符合 F10 契約。") from error

    def intelligence(
        self, ticker: str, *, limit: int = 10
    ) -> FinancialIntelligenceResponse:
        payload = self._request(
            "GET",
            INTELLIGENCE_PATH.format(ticker=ticker),
            params={"limit": limit},
        )
        try:
            return FinancialIntelligenceResponse.model_validate(payload)
        except ValueError as error:
            raise DashboardApiError("本機 intelligence API 回應不符合 F10 契約。") from error

    def _request(self, method: str, path: str, **kwargs: object) -> object:
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                trust_env=False,
                transport=self.transport,
            ) as client:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise DashboardApiError(
                "無法取得本機 FastAPI 資料；請確認服務已啟動且 F7 artifact 可用。"
            ) from error


def _validate_loopback_url(base_url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed = urlsplit(base_url.strip())
    if (
        parsed.scheme != "http"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Dashboard API URL must be a plain HTTP loopback origin")
    if parsed.port is None:
        raise ValueError("Dashboard API URL must include an explicit local port")
    return base_url.strip().rstrip("/")
