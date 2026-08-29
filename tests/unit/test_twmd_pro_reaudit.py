import json
from pathlib import Path

from research.evaluation.twmd_pro_reaudit import (
    TwmdProReauditConfig,
    load_config,
    summarize_payload,
)


def test_reaudit_config_is_bounded() -> None:
    config = load_config(Path("research/configs/twmd_pro_reaudit.v1.json"))
    assert len(config.probes) <= 10
    assert all(int(probe.params["limit"]) <= 2 for probe in config.probes)


def test_reaudit_rejects_bulk_limit() -> None:
    try:
        TwmdProReauditConfig.model_validate(
            {
                "api_key_environment_variable": "TWMD_API_KEY",
                "timeout_seconds": 10,
                "max_response_bytes": 1000,
                "raw_retention": "ignored_local_cache_only",
                "probes": [
                    {
                        "label": "bulk",
                        "endpoint": "https://example.test/data",
                        "params": {"limit": 3},
                    }
                ],
            }
        )
    except ValueError as error:
        assert "limit 1 or 2" in str(error)
    else:
        raise AssertionError("bulk-like probe limit should be rejected")


def test_summary_exposes_schema_but_not_values() -> None:
    payload = (
        b'{"dataset_id":"major_event_taxonomy","data":['
        b'{"ticker":"2330","event_date":"2024-01-02","event_time":"18:00:00",'
        b'"subject":"private sample","event_class":"other"}]}'
    )
    result = summarize_payload(
        label="major_event_taxonomy_2024",
        endpoint="https://example.test/data",
        status_code=200,
        payload_bytes=payload,
        cache_hit=False,
    )
    assert result["access_result"] == "ACCESSIBLE"
    assert result["row_count"] == 1
    assert result["title_or_summary_available"] is True
    assert result["full_text_available"] is False
    assert "private sample" not in str(result)


def test_summary_supports_nested_company_news_envelope() -> None:
    payload = (
        b'{"dataset":"company_news","meta":{"metadata_only":true},"envelope":{"data":['
        b'{"ticker":"2330","published_at":"2024-01-02T08:00:00+08:00",'
        b'"headline":"sample","content_url":"https://example.test"}]}}'
    )
    result = summarize_payload(
        label="company_news_runtime_filters_2024",
        endpoint="https://example.test/data",
        status_code=200,
        payload_bytes=payload,
        cache_hit=False,
        request_params={"ticker": "2330", "limit": 2},
    )
    assert result["row_count"] == 1
    assert result["metadata_only"] is True
    assert result["title_or_summary_available"] is True
    assert result["full_text_available"] is False
    assert result["observed_min_date"] == "2024-01-02"


def test_error_summary_keeps_only_safe_metadata() -> None:
    result = summarize_payload(
        label="company_news_2024",
        endpoint="https://example.test/data",
        status_code=402,
        payload_bytes=None,
        cache_hit=False,
    )
    assert result["access_result"] == "NOT_ENTITLED"
    assert result["payload_sha256"] is None
    assert result["row_fields"] == []


def test_frozen_twmd_source_decision_is_secondary_and_scoped() -> None:
    decision = json.loads(
        Path("research/configs/twmd_pro_source_decision.v1.json").read_text(encoding="utf-8")
    )
    assert decision["overall_classification"] == "ACCEPT_SECONDARY"
    assert decision["dataset_status"]["company_news"].startswith("HOLD_")
    assert decision["dataset_status"]["mops_material_events_private_beta"].startswith("HOLD_")
    assert decision["api_key_recorded"] is False
    assert "B2.1/B2-v2" in decision["b2_b3_gate"]
