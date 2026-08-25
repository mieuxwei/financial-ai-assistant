from pipelines.news.normalization import (
    canonicalize_url,
    fuzzy_title_similarity,
    normalize_title,
)


def test_url_canonicalization_removes_tracking_and_fragment() -> None:
    url = "HTTPS://Example.COM/news/?utm_source=test&id=7#section"
    assert canonicalize_url(url) == "https://example.com/news?id=7"


def test_title_normalization_and_fuzzy_similarity() -> None:
    assert normalize_title(" 台積電（2330）重大訊息！ ") == "台積電2330重大訊息"
    assert fuzzy_title_similarity("台積電董事會重要決議", "台積電：董事會重要決議") >= 0.92

