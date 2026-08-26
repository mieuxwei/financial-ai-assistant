from __future__ import annotations

import hashlib
import re

from research.annotation.schema import EventType, ImpactLabel
from research.weak_supervision.schema import WeakVote

RULE_REVISION = "taiwan-deterministic-rules-v1"

EVENT_TERMS: dict[EventType, tuple[str, ...]] = {
    EventType.EARNINGS: ("財務報告", "稅後淨利", "每股盈餘", "虧損"),
    EventType.REVENUE: ("月營收", "營業收入", "合併營收"),
    EventType.DIVIDEND: ("現金股利", "股票股利", "盈餘分配", "除權息"),
    EventType.BUYBACK: ("庫藏股", "買回股份"),
    EventType.CAPITAL_INCREASE: ("現金增資", "私募", "發行新股"),
    EventType.CAPITAL_REDUCTION: ("減資", "退還股款"),
    EventType.MERGERS_AND_ACQUISITIONS: ("合併案", "股份轉換", "收購"),
    EventType.REGULATORY: ("主管機關", "裁罰", "行政處分", "重大訴訟"),
    EventType.MANAGEMENT_CHANGE: ("董事長異動", "總經理異動", "發言人異動"),
    EventType.GUIDANCE: ("財務預測", "營運展望", "未來展望"),
    EventType.MATERIAL_TRANSACTION: ("重大合約", "取得或處分資產", "背書保證", "資金貸與"),
}

POSITIVE_TERMS = ("營收成長", "獲利增加", "取得重大訂單", "轉虧為盈")
NEGATIVE_TERMS = ("營收衰退", "獲利減少", "發生虧損", "遭裁罰", "停工", "終止合約")


def deterministic_rule_vote(text: str) -> WeakVote:
    normalized = re.sub(r"\s+", " ", text).strip()
    input_sha256 = hashlib.sha256(normalized.encode()).hexdigest()
    event_matches = [
        event_type
        for event_type, terms in EVENT_TERMS.items()
        if any(term in normalized for term in terms)
    ]
    positive = any(term in normalized for term in POSITIVE_TERMS)
    negative = any(term in normalized for term in NEGATIVE_TERMS)
    impact = None
    if positive and negative:
        impact = ImpactLabel.AMBIGUOUS
    elif positive:
        impact = ImpactLabel.POSITIVE
    elif negative:
        impact = ImpactLabel.NEGATIVE
    event_type = event_matches[0] if len(event_matches) == 1 else None
    has_signal = impact is not None or event_type is not None
    return WeakVote(
        labeling_function_id="deterministic_rules",
        labeling_function_revision=RULE_REVISION,
        source_type="deterministic_rule",
        impact_label=impact,
        normalized_event_type=event_type,
        confidence=0.8 if has_signal else 0.0,
        abstention_reason=None if has_signal else "NO_RULE_MATCH",
        input_sha256=input_sha256,
    )
