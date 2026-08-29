from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import httpx

PROBE_VERSION = "b3-gdelt-official-path-recovery-v1"
DEFAULT_ENDPOINT = "https://data.gdeltproject.org/gdeltv3/gal/feed.rss"
DEFAULT_OUTPUT = Path("artifacts/b3-gdelt-official-path-recovery.json")
MAX_RESPONSE_BYTES = 512_000


def summarize_rss(payload: bytes) -> dict[str, object]:
    root = ET.fromstring(payload)
    items = root.findall("./channel/item")
    title_count = 0
    link_count = 0
    publication_time_count = 0
    guid_count = 0
    for item in items:
        title_count += bool((item.findtext("title") or "").strip())
        link_count += bool((item.findtext("link") or "").strip())
        publication_time_count += bool((item.findtext("pubDate") or "").strip())
        guid_count += bool((item.findtext("guid") or "").strip())
    count = len(items)
    return {
        "item_count": count,
        "title_available_rate": title_count / count if count else None,
        "link_available_rate": link_count / count if count else None,
        "publication_time_available_rate": publication_time_count / count if count else None,
        "guid_available_rate": guid_count / count if count else None,
        "full_text_available": False,
        "tone_available": False,
        "raw_values_excluded_from_report": True,
    }


def run_probe(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    output_path: Path = DEFAULT_OUTPUT,
    client: httpx.Client | None = None,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=httpx.Timeout(20.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "financial-ai-assistant/0.1 b3-gdelt-recovery"},
    )
    result: dict[str, object]
    try:
        with active_client.stream(
            "GET",
            endpoint,
            headers={"Range": f"bytes=0-{MAX_RESPONSE_BYTES - 1}"},
        ) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("GDELT RSS response exceeded the bounded probe size")
                chunks.append(chunk)
            payload = b"".join(chunks)
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
        summary = summarize_rss(payload)
        result = {
            "access_status": "ACCESSIBLE_METADATA_ONLY",
            "http_status": 200,
            "content_type": content_type,
            "response_bytes": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            **summary,
        }
    except (httpx.HTTPError, ET.ParseError, ValueError) as error:
        result = {
            "access_status": "TEMPORARILY_UNAVAILABLE",
            "http_status": (
                error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
            ),
            "error_type": type(error).__name__,
            "raw_values_excluded_from_report": True,
        }
    finally:
        if owns_client:
            active_client.close()
    report = {
        "probe_version": PROBE_VERSION,
        "retrieved_at": (retrieved_at or datetime.now(UTC)).isoformat(),
        "endpoint": endpoint,
        "request_count": 1,
        "maximum_response_bytes": MAX_RESPONSE_BYTES,
        "tls_verification_disabled": False,
        "publisher_pages_fetched": False,
        "raw_payload_saved": False,
        "result": result,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one bounded official GDELT RSS recovery.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_probe(endpoint=args.endpoint, output_path=args.output)
    print(
        json.dumps(
            {
                "access_status": report["result"]["access_status"],
                "request_count": 1,
                "tls_verification_disabled": False,
                "raw_payload_saved": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
