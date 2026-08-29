from datetime import date
from pathlib import Path

from jobs.b4_twmd_historical_backfill import load_config, month_windows


def test_backfill_contract_is_private_and_uses_frozen_universe() -> None:
    config = load_config(Path("research/configs/b4_twmd_historical_backfill.v1.json"))
    assert config.date_from == date(2021, 1, 1)
    assert config.date_to == date(2025, 12, 31)
    assert len(config.tickers) == 10
    assert config.maximum_window_days == 31
    assert config.request_limit == 100
    assert config.raw_or_normalized_subject_publication_allowed is False
    assert config.redistribution_allowed is False


def test_month_windows_are_complete_and_nonoverlapping() -> None:
    windows = month_windows(date(2024, 1, 1), date(2024, 3, 15))
    assert windows == [
        (date(2024, 1, 1), date(2024, 1, 31)),
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 3, 1), date(2024, 3, 15)),
    ]
    for previous, current in zip(windows, windows[1:], strict=False):
        assert previous[1].toordinal() + 1 == current[0].toordinal()
