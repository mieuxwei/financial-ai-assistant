class MarketDataError(Exception):
    """Base error for provider, quality, and persistence failures."""


class ProviderUnavailableError(MarketDataError):
    pass


class ProviderResponseError(MarketDataError):
    pass


class MarketDataQualityError(MarketDataError):
    pass
