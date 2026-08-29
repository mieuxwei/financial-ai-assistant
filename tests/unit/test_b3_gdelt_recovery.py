from datetime import UTC, datetime
from pathlib import Path

import httpx

from research.evaluation.b3_gdelt_recovery import run_probe, summarize_rss

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
<title>sample title excluded from report</title>
<link>https://example.test/article</link>
<guid>sample-guid</guid>
<pubDate>Fri, 29 Aug 2026 00:00:00 GMT</pubDate>
</item></channel></rss>"""


def test_rss_summary_contains_only_aggregate_metadata() -> None:
    summary = summarize_rss(RSS)
    assert summary["item_count"] == 1
    assert summary["title_available_rate"] == 1
    assert summary["full_text_available"] is False
    assert summary["tone_available"] is False
    assert "sample title" not in str(summary)
    assert "example.test" not in str(summary)


def test_probe_uses_one_bounded_verified_request_and_saves_no_raw(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Range"].startswith("bytes=0-")
        return httpx.Response(200, content=RSS, headers={"content-type": "application/rss+xml"})

    report = run_probe(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        output_path=tmp_path / "report.json",
        retrieved_at=datetime(2026, 8, 29, tzinfo=UTC),
    )
    assert report["request_count"] == 1
    assert report["tls_verification_disabled"] is False
    assert report["raw_payload_saved"] is False
    assert report["result"]["access_status"] == "ACCESSIBLE_METADATA_ONLY"
    assert report["result"]["item_count"] == 1
