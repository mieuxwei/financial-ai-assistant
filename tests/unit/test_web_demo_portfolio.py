from math import inf, nan

import pytest

from demo.portfolio import (
    FROZEN_UNIVERSE,
    MAX_DEMO_HOLDINGS,
    build_holding,
    delete_holding,
    upsert_holding,
)


def test_portfolio_accepts_frozen_universe_and_updates_without_duplicate() -> None:
    holdings = upsert_holding([], build_holding("2330", 100, 820))
    holdings = upsert_holding(holdings, build_holding("2330", 200, 810))

    assert holdings == [
        {
            "ticker": "2330",
            "company": "台積電",
            "shares": 200.0,
            "average_cost": 810.0,
        }
    ]


def test_portfolio_enforces_five_ticker_limit() -> None:
    holdings = []
    for ticker in tuple(FROZEN_UNIVERSE)[:MAX_DEMO_HOLDINGS]:
        holdings = upsert_holding(holdings, build_holding(ticker, 1, 1))

    with pytest.raises(ValueError, match="最多只能加入 5 檔"):
        upsert_holding(
            holdings,
            build_holding(tuple(FROZEN_UNIVERSE)[MAX_DEMO_HOLDINGS], 1, 1),
        )


@pytest.mark.parametrize(
    ("ticker", "shares", "cost"),
    (("9999", 1, 1), ("2330", -1, 1), ("2330", nan, 1), ("2330", 1, inf)),
)
def test_portfolio_rejects_invalid_inputs(ticker: str, shares: float, cost: float) -> None:
    with pytest.raises(ValueError):
        build_holding(ticker, shares, cost)


def test_delete_holding_is_ticker_scoped() -> None:
    holdings = [build_holding("2330", 100, 820), build_holding("0050", 10, 150)]
    assert delete_holding(holdings, "2330") == [build_holding("0050", 10, 150)]
