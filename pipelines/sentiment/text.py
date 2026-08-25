import hashlib


def build_sentiment_text(title: str, summary: str | None) -> str:
    parts = [title.strip()]
    if summary and summary.strip() and summary.strip() != title.strip():
        parts.append(summary.strip())
    return "\n".join(parts)


def sentiment_input_hash(text: str, model_version: str) -> str:
    return hashlib.sha256(f"{model_version}|{text}".encode()).hexdigest()


def supports_language(language: str, prefixes: tuple[str, ...]) -> bool:
    normalized = language.strip().casefold()
    return any(
        normalized == prefix.casefold()
        or normalized.startswith(f"{prefix.casefold()}-")
        for prefix in prefixes
    )
