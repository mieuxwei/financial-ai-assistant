from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictDemoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _finite_positive(value: Decimal) -> Decimal:
    if not value.is_finite() or value <= 0:
        raise ValueError("value must be finite and greater than zero")
    return value


class DemoHoldingCreate(StrictDemoSchema):
    ticker: str = Field(pattern=r"^[0-9]{4}$")
    shares: Decimal
    average_cost: Decimal

    _shares_positive = field_validator("shares")(_finite_positive)
    _cost_positive = field_validator("average_cost")(_finite_positive)


class DemoHoldingUpdate(StrictDemoSchema):
    shares: Decimal
    average_cost: Decimal
    version: int = Field(ge=1)

    _shares_positive = field_validator("shares")(_finite_positive)
    _cost_positive = field_validator("average_cost")(_finite_positive)


class DemoHoldingResponse(StrictDemoSchema):
    id: str
    ticker: str
    company: str
    shares: Decimal
    average_cost: Decimal
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    version: int


class DemoPortfolioResponse(StrictDemoSchema):
    contract_version: Literal["line-public-beta-portfolio-v1"] = "line-public-beta-portfolio-v1"
    demo_label: Literal["DEMO SANDBOX PORTFOLIO"] = "DEMO SANDBOX PORTFOLIO"
    max_holdings: int
    retention_days: int
    holdings: list[DemoHoldingResponse]
    current_price_available: Literal[False] = False
    roi_available: Literal[False] = False
    limitation: str


class DemoPrincipalResponse(StrictDemoSchema):
    contract_version: Literal["line-public-beta-principal-v1"] = "line-public-beta-principal-v1"
    disclosure_accepted: bool
    expires_at: datetime | None


class DemoMutationResponse(StrictDemoSchema):
    operation: Literal["created", "updated", "deleted", "disclosure_accepted"]
    applied: bool
    holding: DemoHoldingResponse | None = None


class DemoDeleteMeResponse(StrictDemoSchema):
    operation: Literal["delete_my_demo_data"] = "delete_my_demo_data"
    deleted: bool
    message: str = "Demo sandbox data deleted"


class DemoResearchSignal(StrictDemoSchema):
    status: Literal["CONTROLLED_RESEARCH_SIGNAL", "UNAVAILABLE_FOR_CONTROLLED_FIXTURE"]
    fixture_id: str | None
    score: float | None
    historical_percentile: float | None
    communication_band: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"] | None
    direction: None = None
    current_market_inference: Literal[False] = False

    @field_validator("score", "historical_percentile")
    @classmethod
    def finite_when_present(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("research values must be finite")
        return value


class DemoIntelligenceSignal(StrictDemoSchema):
    status: Literal["CONTROLLED_RESEARCH_INTELLIGENCE", "UNAVAILABLE_FOR_CONTROLLED_FIXTURE"]
    event_class: str | None
    event_summary: str | None
    market_reaction_magnitude: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"] | None
    direction: None = None
    chinese_sentiment: None = None
    chinese_sentiment_message: str


class DemoPortfolioHealthItem(StrictDemoSchema):
    holding: DemoHoldingResponse
    research: DemoResearchSignal
    intelligence: DemoIntelligenceSignal
    reference_price: None = None
    reference_price_date: None = None
    roi: None = None


class DemoPortfolioHealthResponse(StrictDemoSchema):
    contract_version: Literal["line-public-beta-health-v1"] = "line-public-beta-health-v1"
    demo_label: Literal["CONTROLLED RESEARCH SIGNAL"] = "CONTROLLED RESEARCH SIGNAL"
    items: list[DemoPortfolioHealthItem]
    limitation: str


class DemoStockAnalysisResponse(StrictDemoSchema):
    contract_version: Literal["line-public-beta-stock-analysis-v1"] = (
        "line-public-beta-stock-analysis-v1"
    )
    ticker: str
    company: str
    research: DemoResearchSignal
    limitation: str


class DemoFinancialIntelligenceResponse(StrictDemoSchema):
    contract_version: Literal["line-public-beta-intelligence-v1"] = (
        "line-public-beta-intelligence-v1"
    )
    ticker: str
    company: str
    intelligence: DemoIntelligenceSignal
    limitation: str
