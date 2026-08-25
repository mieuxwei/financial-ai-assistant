from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from pipelines.market_data.types import MarketBar, MarketDataRequest


@dataclass(frozen=True)
class MarketDataQualityReport:
    ticker: str
    provider_symbol: str
    source: str
    requested_start: str
    requested_end: str
    row_count: int
    first_date: str | None
    last_date: str | None
    potential_missing_weekdays: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fatal_issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.fatal_issues

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "passed": self.passed}


def assess_market_data(
    request: MarketDataRequest,
    bars: list[MarketBar],
    provider_warnings: list[str] | None = None,
) -> MarketDataQualityReport:
    dates = [bar.trading_date for bar in bars]
    unique_dates = set(dates)
    fatal_issues: list[str] = []
    warnings = list(provider_warnings or [])

    if not bars:
        fatal_issues.append("provider returned no complete bars")
    if len(dates) != len(unique_dates):
        fatal_issues.append("duplicate trading dates detected")

    for bar in bars:
        if bar.ticker != request.ticker:
            fatal_issues.append(f"ticker mismatch on {bar.trading_date.isoformat()}")
        if not request.start_date <= bar.trading_date <= request.end_date:
            fatal_issues.append(f"bar outside requested range on {bar.trading_date.isoformat()}")
        if min(bar.open, bar.high, bar.low, bar.close, bar.adjusted_close) <= 0:
            fatal_issues.append(f"non-positive price on {bar.trading_date.isoformat()}")
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            fatal_issues.append(f"invalid OHLC range on {bar.trading_date.isoformat()}")
        if bar.high < bar.low:
            fatal_issues.append(f"high below low on {bar.trading_date.isoformat()}")
        if bar.volume < 0:
            fatal_issues.append(f"negative volume on {bar.trading_date.isoformat()}")

    missing_weekdays = [
        value.isoformat()
        for value in _weekdays(request.start_date, request.end_date)
        if value not in unique_dates
    ]
    if missing_weekdays:
        warnings.append(
            "potential weekday gaps require exchange-calendar or holiday verification"
        )

    sorted_dates = sorted(unique_dates)
    return MarketDataQualityReport(
        ticker=request.ticker,
        provider_symbol=request.provider_symbol,
        source=bars[0].source if bars else "unknown",
        requested_start=request.start_date.isoformat(),
        requested_end=request.end_date.isoformat(),
        row_count=len(bars),
        first_date=sorted_dates[0].isoformat() if sorted_dates else None,
        last_date=sorted_dates[-1].isoformat() if sorted_dates else None,
        potential_missing_weekdays=missing_weekdays,
        warnings=warnings,
        fatal_issues=list(dict.fromkeys(fatal_issues)),
    )


def _weekdays(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)
