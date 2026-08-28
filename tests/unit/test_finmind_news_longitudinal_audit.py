from datetime import UTC, date, datetime
from pathlib import Path

from research.evaluation.finmind_news_longitudinal_audit import (
    FinMindLongitudinalAuditConfig,
    analyze_rows,
    build_report,
    build_request_plan,
)


def _config() -> FinMindLongitudinalAuditConfig:
    return FinMindLongitudinalAuditConfig.model_validate(
        {
            "endpoint": "https://example.test/data",
            "dataset_id": "TaiwanStockNews",
            "tickers": ["2330"],
            "start_year": 2024,
            "end_year": 2024,
            "sampling_mode": "quarterly_weekday_sample",
            "sample_months": [2, 5, 8, 11],
            "sample_weekday": 2,
            "sample_day_on_or_after": 14,
            "maximum_requests": 4,
            "max_workers": 1,
            "timeout_seconds": 10,
            "max_response_bytes": 10000,
            "required_fields": ["date", "stock_id", "link", "source", "title"],
            "optional_fields": ["description"],
            "token_environment_variable": "FINMIND_API_TOKEN",
            "raw_retention": "ignored_local_cache_only",
            "timestamp_semantics_documented": False,
            "timezone_documented": False,
            "thresholds": {
                "minimum_title_characters": 10,
                "minimum_combined_characters": 30,
                "minimum_usable_content_rate": 0.5,
                "minimum_nonempty_description_rate": 0.5,
                "maximum_exact_link_duplicate_rate": 0.6,
            },
        }
    )


def test_request_plan_spans_all_presealed_year_quarters() -> None:
    plan = build_request_plan(_config())

    assert len(plan) == 4
    assert all(unit.requested_date.weekday() == 2 for unit in plan)
    assert all(unit.requested_date.year == 2024 for unit in plan)


def test_row_audit_measures_timestamp_duplicates_and_content_without_retaining_text() -> None:
    config = _config()
    rows = [
        {
            "date": "2024-02-14 09:30:00",
            "stock_id": "2330",
            "description": "這是一段足夠長度的公司營運新聞摘要，可供事件特徵研究使用。",
            "link": "https://publisher.test/a?utm_source=test",
            "source": "publisher",
            "title": "台積電公布重要營運消息與後續規劃",
        },
        {
            "date": "2024-02-14 09:30:00+08:00",
            "stock_id": "2330",
            "description": "",
            "link": "https://publisher.test/a",
            "source": "publisher",
            "title": "台積電公布重要營運消息與後續規劃",
        },
    ]
    observation = analyze_rows(
        ticker="2330", requested_date=date(2024, 2, 14), rows=rows, config=config
    )
    date_path = Path(".tools/test")
    report = build_report(
        config,
        [
            {
                "ticker": "2330",
                "requested_date": "2024-02-14",
                "payload_sha256": "a" * 64,
                "cache_hit": False,
                "rows": rows,
            }
        ],
        observed_at=datetime(2026, 8, 28, tzinfo=UTC),
        cache_dir=date_path,
    )

    assert observation.valid_timestamp_count == 2
    assert observation.timezone_aware_count == 1
    assert report["aggregate"]["exact_link_duplicate_count"] == 1
    assert report["aggregate"]["nonempty_description_rate"] == 0.5
    assert report["title_level_feature_gate_passed"] is True
    assert report["rich_text_feature_gate_passed"] is True
    assert report["market_reaction_weak_supervision_decision"] == "HOLD"
    assert report["raw_content_committed"] is False
    assert "營運新聞摘要" not in str(report)
    assert str(date_path) in report["local_cache_path"]


def test_config_rejects_sealed_test_year() -> None:
    payload = _config().model_dump(mode="json")
    payload["end_year"] = 2025

    try:
        FinMindLongitudinalAuditConfig.model_validate(payload)
    except ValueError as error:
        assert "sealed-test" in str(error)
    else:
        raise AssertionError("sealed-test year should have been rejected")
