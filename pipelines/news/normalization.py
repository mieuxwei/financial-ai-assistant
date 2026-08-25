import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_KEYS = {"fbclid", "gclid", "utm_campaign", "utm_content", "utm_medium", "utm_source"}


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]+", "", normalized)


def title_fingerprint(title: str) -> str:
    return hashlib.sha256(normalize_title(title).encode()).hexdigest()


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.casefold() not in TRACKING_QUERY_KEYS
        )
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, query, ""))


def content_hash(
    title: str,
    canonical_url: str,
    published_at_iso: str,
    external_id: str | None = None,
) -> str:
    identity = "|".join(
        (normalize_title(title), canonical_url, published_at_iso, external_id or "")
    )
    return hashlib.sha256(identity.encode()).hexdigest()


def fuzzy_title_similarity(left: str, right: str) -> float:
    normalized_left = normalize_title(left)
    normalized_right = normalize_title(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()
