import json
from datetime import timedelta

import httpx

from pipelines.news.tpex_material import TpexMaterialAnnouncementProvider
from pipelines.news.twse_material import TwseMaterialAnnouncementProvider
from pipelines.news.twse_rss import TwseNewsRssProvider


def test_twse_material_parses_roc_datetime_and_strips_field_name() -> None:
    payload = [
        {
            "發言日期": "1150825",
            "發言時間": "64926",
            "公司代號": "2330",
            "公司名稱": "臺灣積體電路股份有限公司",
            "主旨 ": "董事會重要決議",
            "符合條款": "第14款",
            "事實發生日": "1150825",
            "說明": "公開資訊說明",
        }
    ]
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    provider = TwseMaterialAnnouncementProvider(client=client, max_retries=1)

    item = provider.fetch()[0]

    assert item.explicit_tickers == ("2330",)
    assert item.published_at.isoformat() == "2026-08-25T06:49:26+08:00"
    assert item.summary == "公開資訊說明"


def test_twse_rss_keeps_short_excerpt_not_raw_html() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
         xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
      <channel><item>
        <title>TWSE test news</title><link>/rwd/zh/news/newsDetail/1</link>
        <guid>news-1</guid><dc:date>2026-08-25T02:30:00Z</dc:date>
        <content:encoded><![CDATA[<p>short <strong>public</strong> excerpt</p>]]></content:encoded>
      </item></channel>
    </rss>"""
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml))
    )
    item = TwseNewsRssProvider(client=client, max_retries=1).fetch()[0]

    assert item.url == "https://www.twse.com.tw/rwd/zh/news/newsDetail/1"
    assert item.published_at.utcoffset() == timedelta(0)
    assert item.summary == "short public excerpt"
    assert "<p>" not in (item.summary or "")


def test_tpex_material_parses_official_csv_without_frontend_scraping() -> None:
    csv_payload = (
        "出表日期,發言日期,發言時間,公司代號,公司名稱,主旨,符合條款,事實發生日,說明\n"
        "1150829,1150829,174501,9999,測試上櫃公司,董事會決議,第14款,1150829,官方說明\n"
    ).encode("utf-8-sig")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=csv_payload, headers={"content-type": "text/csv"}
            )
        )
    )

    item = TpexMaterialAnnouncementProvider(client=client, max_retries=1).fetch()[0]

    assert item.source == "tpex_openapi_daily_material"
    assert item.explicit_tickers == ("9999",)
    assert item.published_at.isoformat() == "2026-08-29T17:45:01+08:00"
    assert item.summary == "官方說明"


def test_official_providers_expose_raw_batches_for_private_b2_lineage() -> None:
    twse_raw = json.dumps(
        [
            {
                "發言日期": "1150825",
                "發言時間": "064926",
                "公司代號": "2330",
                "公司名稱": "台積電",
                "主旨": "說明",
            }
        ],
        ensure_ascii=False,
    ).encode()
    twse_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=twse_raw, headers={"content-type": "application/json"}
            )
        )
    )
    twse = TwseMaterialAnnouncementProvider(client=twse_client, max_retries=1).fetch_batch()

    tpex_raw = "\ufeff出表日期,發言日期,發言時間,公司代號,公司名稱,主旨\n".encode()
    tpex_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=tpex_raw, headers={"content-type": "text/csv"}
            )
        )
    )
    tpex = TpexMaterialAnnouncementProvider(client=tpex_client, max_retries=1).fetch_batch()

    assert twse.raw_payload == twse_raw
    assert len(twse.items) == 1
    assert tpex.raw_payload == tpex_raw
    assert tpex.items == ()
