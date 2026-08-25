class NewsProviderError(RuntimeError):
    """Base error for a news provider contract failure."""


class NewsProviderUnavailableError(NewsProviderError):
    """Raised after retryable network failures are exhausted."""


class NewsProviderResponseError(NewsProviderError):
    """Raised when a provider response does not match the expected schema."""

