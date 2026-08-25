import pytest

from backend.app.services.tickers import normalize_ticker


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("'0050", "0050"),
        ("2330.tw", "2330"),
        (" 6488.TWO ", "6488"),
        ("AAPL", "AAPL"),
    ],
)
def test_normalize_ticker(raw: str, expected: str) -> None:
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", ["", "2330/", "=IMPORTXML", "台積電"])
def test_normalize_ticker_rejects_unsupported_values(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_ticker(raw)
