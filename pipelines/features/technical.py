from __future__ import annotations

import math
from collections.abc import Sequence


def pct_change(values: Sequence[float], index: int, lag: int) -> float | None:
    if index < lag or values[index - lag] == 0:
        return None
    return _rounded(values[index] / values[index - lag] - 1.0)


def moving_average_deviation(values: Sequence[float], index: int, window: int) -> float | None:
    sample = _window(values, index, window)
    if sample is None:
        return None
    mean = sum(sample) / window
    return None if mean == 0 else _rounded(values[index] / mean - 1.0)


def rolling_zscore(values: Sequence[float], index: int, window: int) -> float | None:
    sample = _window(values, index, window)
    if sample is None:
        return None
    mean = sum(sample) / window
    variance = sum((value - mean) ** 2 for value in sample) / window
    standard_deviation = math.sqrt(variance)
    return 0.0 if standard_deviation == 0 else _rounded((values[index] - mean) / standard_deviation)


def historical_volatility(closes: Sequence[float], index: int, window: int) -> float | None:
    if index < window:
        return None
    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(index - window + 1, index + 1)]
    mean = sum(returns) / window
    variance = sum((value - mean) ** 2 for value in returns) / window
    return _rounded(math.sqrt(variance))


def rsi(closes: Sequence[float], index: int, window: int = 14) -> float | None:
    if index < window:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(index - window + 1, index + 1)]
    average_gain = sum(max(change, 0.0) for change in changes) / window
    average_loss = sum(max(-change, 0.0) for change in changes) / window
    if average_gain == average_loss == 0:
        return 50.0
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return _rounded(100.0 - 100.0 / (1.0 + relative_strength))


def ema_series(values: Sequence[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (span + 1.0)
    output = [float(values[0])]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def macd_series(closes: Sequence[float]) -> tuple[list[float], list[float]]:
    fast = ema_series(closes, 12)
    slow = ema_series(closes, 26)
    macd = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow, strict=True)]
    signal = ema_series(macd, 9)
    return macd, signal


def _window(values: Sequence[float], index: int, window: int) -> Sequence[float] | None:
    if index + 1 < window:
        return None
    return values[index - window + 1 : index + 1]


def _rounded(value: float) -> float:
    return round(value, 10)
