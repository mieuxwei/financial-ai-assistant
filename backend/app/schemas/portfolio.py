from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.services.tickers import normalize_ticker


class HoldingValues(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    cost_basis: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    take_profit_pct: Decimal = Field(default=Decimal("20"), ge=-100, le=1000)
    stop_loss_pct: Decimal = Field(default=Decimal("-10"), ge=-100, le=1000)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.startswith(("=", "+", "-", "@")):
            raise ValueError("name cannot begin with a spreadsheet formula marker")
        return normalized


class HoldingCreate(HoldingValues):
    pass


class HoldingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=4)
    cost_basis: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)
    take_profit_pct: Decimal | None = Field(default=None, ge=-100, le=1000)
    stop_loss_pct: Decimal | None = Field(default=None, ge=-100, le=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return HoldingValues.strip_name(value)


class HoldingResponse(HoldingValues):
    model_config = ConfigDict(from_attributes=True)

    id: str
    portfolio_id: str
    created_at: datetime
    updated_at: datetime


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    is_demo: bool
    holdings: list[HoldingResponse]


class PortfolioSyncPreviewRequest(BaseModel):
    holdings: list[HoldingCreate] = Field(max_length=10)

    @model_validator(mode="after")
    def reject_duplicate_tickers(self) -> "PortfolioSyncPreviewRequest":
        tickers = [holding.ticker for holding in self.holdings]
        if len(tickers) != len(set(tickers)):
            raise ValueError("holdings must contain unique tickers")
        return self


class PortfolioSyncPreviewResponse(BaseModel):
    operation_id: str
    expires_at: datetime
    additions: int
    updates: int
    removals: int
    holdings: list[HoldingCreate]


class PortfolioSyncConfirmResponse(BaseModel):
    operation_id: str
    status: str
    applied: bool
    portfolio: PortfolioResponse
