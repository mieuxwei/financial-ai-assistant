from datetime import UTC, datetime

import httpx

from research.evaluation.finmind_news_audit import (
    FinMindNewsAuditConfig,
    audit_finmind_news,
)


def test_finmind_news_audit_retains_only_aggregate_metadata() -> None:
    config = FinMindNewsAuditConfig.model_validate(
        {
            "endpoint": "https://example.test/data",
            "dataset_id": "TaiwanStockNews",
            "ticker": "2330",
            "sample_dates": ["2024-04-01"],
            "required_fields": [
                "date",
                "stock_id",
                "description",
                "link",
                "source",
                "title",
            ],
            "max_response_bytes": 10000,
            "timestamp_semantics_documented": False,
            "timezone_documented": False,
            "retention_policy": "aggregate_hashes_only",
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["start_date"] == "2024-04-01"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "date": "2024-04-01 08:30:00",
                        "stock_id": "2330",
                        "description": "private-to-report text",
                        "link": "https://publisher.test/a",
                        "source": "publisher",
                        "title": "private-to-report title",
                    },
                    {
                        "date": "2024-04-01 08:30:00",
                        "stock_id": "2330",
                        "description": "duplicate",
                        "link": "https://publisher.test/a",
                        "source": "publisher",
                        "title": "duplicate title",
                    },
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = audit_finmind_news(
            config,
            client=client,
            retrieved_at=datetime(2026, 8, 26, tzinfo=UTC),
        )

    serialized = str(report)
    assert report["schema_gate_passed"] is True
    assert report["record_count"] == 2
    assert report["exact_link_duplicate_count"] == 1
    assert report["timezone_aware_timestamp_count"] == 0
    assert report["direct_reaction_event_decision"] == "HOLD"
    assert "private-to-report" not in serialized
    assert "publisher.test" not in serialized
