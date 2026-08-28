from datetime import UTC, date, datetime
from pathlib import Path

from research.evaluation.twmd_major_event_probe import (
    ProbePeriod,
    TwmdProbeConfig,
    summarize_result,
)


def _config() -> TwmdProbeConfig:
    return TwmdProbeConfig.model_validate(
        {
            "endpoint": "https://example.test/v2/datasets/major-event-taxonomy",
            "symbol": "2330",
            "periods": [
                {"label": "history_2024", "start_date": "2024-01-01", "end_date": "2024-12-31"}
            ],
            "limit": 100,
            "timeout_seconds": 10,
            "max_response_bytes": 10000,
            "api_key_environment_variable": "TWMD_API_KEY",
            "raw_retention": "ignored_local_cache_only",
        }
    )


def test_period_rejects_sealed_test_boundary() -> None:
    try:
        ProbePeriod(label="sealed", start_date=date(2025, 1, 1), end_date=date(2025, 1, 2))
    except ValueError as error:
        assert "sealed-test" in str(error)
    else:
        raise AssertionError("sealed-test dates should be rejected")


def test_summary_excludes_subject_text_and_measures_quality() -> None:
    result = {
        "label": "history_2024",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "status_code": 200,
        "cache_hit": False,
        "payload_sha256": "a" * 64,
        "declared_data_count": 2,
        "known_gaps": [],
        "warnings": [],
        "rows": [
            {
                "ticker": "2330",
                "market": "TW",
                "event_date": "2024-01-03",
                "event_time": "17:01:02",
                "subject": "不應出現在稽核報告的逐字主旨",
                "event_class": "其他",
                "confidence": 0.5,
                "rule_version": "mops_taxonomy_v1",
            },
            {
                "ticker": "2330",
                "market": "TW",
                "event_date": "2024-01-03",
                "event_time": "17:01:02",
                "subject": "不應出現在稽核報告的逐字主旨",
                "event_class": "其他",
                "confidence": 0.5,
                "rule_version": "mops_taxonomy_v1",
            },
        ],
    }

    summary = summarize_result(result, symbol="2330", limit=_config().limit)

    assert summary["exact_identity_duplicate_count"] == 1
    assert summary["valid_event_time_rate"] == 1
    assert summary["required_fields_present_in_all_rows"] is True
    assert summary["raw_subjects_excluded_from_report"] is True
    assert "逐字主旨" not in str(summary)


def test_summary_retains_only_safe_http_error_metadata() -> None:
    summary = summarize_result(
        {
            "label": "history_2018",
            "start_date": "2018-01-01",
            "end_date": "2018-12-31",
            "status_code": 402,
            "cache_hit": False,
            "payload_sha256": None,
            "declared_data_count": None,
            "known_gaps": [],
            "warnings": [],
            "error_code": "HTTP_402",
            "rows": [],
        },
        symbol="2330",
        limit=100,
    )

    assert summary["status_code"] == 402
    assert summary["error_code"] == "HTTP_402"
    assert summary["row_count"] == 0


def test_fixture_imports_are_stable() -> None:
    assert datetime(2026, 8, 29, tzinfo=UTC).tzinfo is UTC
    assert Path(".env").name == ".env"
