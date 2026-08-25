import re

TICKER_PATTERN = re.compile(r"^[0-9A-Z][0-9A-Z.-]{0,19}$")


def normalize_ticker(value: str) -> str:
    ticker = value.strip().lstrip("'").upper()
    if ticker.endswith(".TWO"):
        ticker = ticker.removesuffix(".TWO")
    elif ticker.endswith(".TW"):
        ticker = ticker.removesuffix(".TW")
    if not ticker or not TICKER_PATTERN.fullmatch(ticker):
        raise ValueError("ticker contains unsupported characters")
    return ticker
