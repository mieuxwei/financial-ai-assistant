import json
import re
from pathlib import Path

from backend.app.services.tickers import normalize_ticker
from pipelines.news.types import NewsItem, TickerMatch


class TickerMatcher:
    def __init__(self, aliases: dict[str, tuple[str, ...]]) -> None:
        self.aliases = {
            normalize_ticker(ticker): tuple(alias.strip() for alias in names if alias.strip())
            for ticker, names in aliases.items()
        }

    @classmethod
    def from_file(cls, path: Path) -> "TickerMatcher":
        payload = json.loads(path.read_text(encoding="utf-8"))
        instruments = payload.get("instruments")
        if not isinstance(instruments, list) or not instruments:
            raise ValueError("ticker alias config must contain a non-empty instruments list")
        return cls(
            {
                str(item["ticker"]): tuple(str(alias) for alias in item.get("aliases", []))
                for item in instruments
            }
        )

    def match(self, item: NewsItem) -> list[TickerMatch]:
        best: dict[str, TickerMatch] = {}
        for ticker in item.explicit_tickers:
            normalized = normalize_ticker(ticker)
            best[normalized] = TickerMatch(normalized, 1.0, "official_company_code")

        title = item.title.casefold()
        summary = (item.summary or "").casefold()
        for ticker, aliases in self.aliases.items():
            candidates = [
                self._match_ticker(ticker, title, 0.95, "ticker_title"),
                self._match_aliases(aliases, title, 0.9, "company_alias_title"),
                self._match_ticker(ticker, summary, 0.75, "ticker_summary"),
                self._match_aliases(aliases, summary, 0.65, "company_alias_summary"),
            ]
            matches = [candidate for candidate in candidates if candidate]
            if matches:
                score, method = max(matches, key=lambda value: value[0])
                current = best.get(ticker)
                if current is None or score > current.relevance_score:
                    best[ticker] = TickerMatch(ticker, score, method)
        return sorted(best.values(), key=lambda match: match.ticker)

    @staticmethod
    def _match_ticker(
        ticker: str, text: str, score: float, method: str
    ) -> tuple[float, str] | None:
        pattern = rf"(?<![0-9A-Za-z]){re.escape(ticker.casefold())}(?![0-9A-Za-z])"
        return (score, method) if re.search(pattern, text) else None

    @staticmethod
    def _match_aliases(
        aliases: tuple[str, ...], text: str, score: float, method: str
    ) -> tuple[float, str] | None:
        return (score, method) if any(alias.casefold() in text for alias in aliases) else None

