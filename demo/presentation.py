from __future__ import annotations

from typing import Literal

from backend.app.schemas.research import FinancialIntelligenceItem

Band = Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]

BAND_PRESENTATION: dict[Band, tuple[str, str]] = {
    "LOW": ("低", "#1f9d74"),
    "MODERATE": ("中等", "#c58a17"),
    "HIGH": ("高", "#d96945"),
    "VERY_HIGH": ("非常高", "#c23b53"),
}


def band_label(band: Band) -> str:
    return BAND_PRESENTATION[band][0]


def band_color(band: Band) -> str:
    return BAND_PRESENTATION[band][1]


def format_score(value: str) -> str:
    return f"{float(value):.2f}×"


def format_percentile(value: float) -> str:
    return f"{value:.1f}%"


def sentiment_summary(item: FinancialIntelligenceItem) -> str:
    sentiment = item.sentiment
    if sentiment.status == "SCORED":
        labels = {"positive": "正向", "neutral": "中立", "negative": "負向"}
        label = labels.get(sentiment.label or "", sentiment.label or "未知")
        return f"英文 FinBERT：{label}（score {sentiment.score or 0:+.2f}）"
    if sentiment.abstention_reason == "CHINESE_SENTIMENT_NOT_VALIDATED":
        return "中文情緒：不輸出（尚未通過驗證）"
    if sentiment.status == "ELIGIBLE_NOT_SCORED":
        return "英文情緒：可評分，但此紀錄尚未執行模型"
    return "情緒：不支援／未評分"


def event_summary(item: FinancialIntelligenceItem) -> str:
    event = item.event_intelligence
    if event.status == "ABSTAIN":
        return "事件規則：無明確訊號"
    event_type = event.normalized_event_type or "未分類"
    impact = event.impact_proxy or "未判定"
    return f"事件代理：{event_type}／{impact}（非情緒 ground truth）"
