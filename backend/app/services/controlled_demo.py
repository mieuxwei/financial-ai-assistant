from __future__ import annotations

from pathlib import Path
from typing import Literal

from backend.app.core.errors import NotFoundError, ServiceUnavailableError
from backend.app.schemas.controlled_demo import ControlledLineDemoResponse
from demo.contracts import ControlledDashboardFixture, load_controlled_fixture

CONTROLLED_TICKER = "2330"
DemoView = Literal["STOCK_ANALYSIS", "FINANCIAL_INTELLIGENCE"]


class ControlledLineDemoService:
    def __init__(self, fixture_path: Path) -> None:
        try:
            self.fixture = load_controlled_fixture(fixture_path)
        except (OSError, ValueError) as error:
            raise ServiceUnavailableError("controlled LINE fixture is unavailable") from error
        self._validate_fixture(self.fixture)

    def get(self, view: DemoView, ticker: str) -> ControlledLineDemoResponse:
        normalized = ticker.strip().upper().removesuffix(".TW")
        if normalized != CONTROLLED_TICKER:
            raise NotFoundError("controlled demo is available only for the designated fixture")
        if view not in {"STOCK_ANALYSIS", "FINANCIAL_INTELLIGENCE"}:
            raise NotFoundError("controlled demo view is unavailable")

        fixture = self.fixture
        chinese = next(
            item for item in fixture.intelligence_items if item.language.casefold().startswith("zh")
        )
        common = {
            "contract_version": "f11b-controlled-line-demo-v1",
            "demo_label": "CONTROLLED RESEARCH DEMO",
            "view": view,
            "ticker": CONTROLLED_TICKER,
            "company_display_name": fixture.company_display_name,
            "fixture_id": fixture.fixture_id,
            "data_notice": fixture.data_notice,
            "boundary": {
                "fixture_only": True,
                "read_only": True,
                "live_market_data": False,
                "external_api_called": False,
                "model_inference_performed": False,
                "portfolio_read": False,
                "portfolio_write": False,
            },
            "disclaimer": (
                "受控合成研究展示；不預測上漲或下跌方向，不是即時資料或投資建議。"
            ),
        }
        if view == "STOCK_ANALYSIS":
            prediction = fixture.prediction_response
            return ControlledLineDemoResponse(
                **common,
                stock_analysis={
                    "risk_band": prediction.risk_band,
                    "historical_percentile": prediction.historical_percentile,
                    "risk_explanation": (
                        "相對於該合成股票自身歷史狀態的下一交易日波動異常程度。"
                    ),
                    "current_price": None,
                    "daily_change": None,
                    "ma5": None,
                    "ma20": None,
                    "recent_event_summary": chinese.source_excerpt or "受控事件範例",
                    "market_reaction_magnitude": None,
                },
                financial_intelligence=None,
            )

        return ControlledLineDemoResponse(
            **common,
            stock_analysis=None,
            financial_intelligence={
                "recent_financial_event": chinese.source_excerpt or "受控事件範例",
                "event_class": chinese.event_intelligence.normalized_event_type,
                "event_timestamp": chinese.published_at,
                "event_source": chinese.source,
                "market_reaction_magnitude": None,
                "historical_percentile": None,
                "direction_supported": False,
                "chinese_sentiment_validated": False,
            },
        )

    @staticmethod
    def _validate_fixture(fixture: ControlledDashboardFixture) -> None:
        if (
            not fixture.controlled_synthetic_data
            or fixture.actual_market_observation
            or fixture.private_or_user_data
            or fixture.prediction_request.ticker != CONTROLLED_TICKER
        ):
            raise ServiceUnavailableError("controlled LINE fixture boundary is invalid")
