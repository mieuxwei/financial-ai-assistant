from pathlib import Path

from scripts.import_holdings import parse_csv


def test_parse_synthetic_holdings_fixture() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "holdings.csv"

    holdings = parse_csv(fixture)

    assert [holding.ticker for holding in holdings] == ["0050", "2330"]
    assert all(holding.name.startswith("Synthetic") for holding in holdings)
