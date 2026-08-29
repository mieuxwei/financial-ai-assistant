from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ControlledDemoBoundary(StrictSchema):
    fixture_only: Literal[True]
    read_only: Literal[True]
    live_market_data: Literal[False]
    external_api_called: Literal[False]
    model_inference_performed: Literal[False]
    portfolio_read: Literal[False]
    portfolio_write: Literal[False]


class ControlledStockAnalysis(StrictSchema):
    risk_band: Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    historical_percentile: float = Field(ge=0, le=100)
    risk_explanation: str
    current_price: None
    daily_change: None
    ma5: None
    ma20: None
    recent_event_summary: str
    market_reaction_magnitude: None


class ControlledFinancialIntelligence(StrictSchema):
    recent_financial_event: str
    event_class: str | None
    event_timestamp: datetime
    event_source: str
    market_reaction_magnitude: None
    historical_percentile: None
    direction_supported: Literal[False]
    chinese_sentiment_validated: Literal[False]


class ControlledLineDemoResponse(StrictSchema):
    contract_version: Literal["f11b-controlled-line-demo-v1"]
    demo_label: Literal["CONTROLLED RESEARCH DEMO"]
    view: Literal["STOCK_ANALYSIS", "FINANCIAL_INTELLIGENCE"]
    ticker: Literal["2330"]
    company_display_name: str
    fixture_id: Literal["synthetic-2330-f11-v1"]
    data_notice: str
    stock_analysis: ControlledStockAnalysis | None
    financial_intelligence: ControlledFinancialIntelligence | None
    boundary: ControlledDemoBoundary
    disclaimer: str

    @model_validator(mode="after")
    def require_only_selected_view(self) -> ControlledLineDemoResponse:
        if self.view == "STOCK_ANALYSIS":
            if self.stock_analysis is None or self.financial_intelligence is not None:
                raise ValueError("controlled stock-analysis payload drifted")
        elif self.financial_intelligence is None or self.stock_analysis is not None:
            raise ValueError("controlled financial-intelligence payload drifted")
        return self
