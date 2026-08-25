from collections import Counter

LABELS = ("positive", "neutral", "negative")


def classification_report(
    expected: list[str], predicted: list[str]
) -> dict[str, object]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("expected and predicted must be non-empty and equal length")
    confusion = Counter(zip(expected, predicted, strict=True))
    per_class: dict[str, dict[str, float | int]] = {}
    for label in LABELS:
        true_positive = confusion[(label, label)]
        false_positive = sum(confusion[(other, label)] for other in LABELS if other != label)
        false_negative = sum(confusion[(label, other)] for other in LABELS if other != label)
        support = sum(confusion[(label, other)] for other in LABELS)
        precision = _ratio(true_positive, true_positive + false_positive)
        recall = _ratio(true_positive, true_positive + false_negative)
        f1 = _ratio(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return {
        "accuracy": sum(left == right for left, right in confusion.elements())
        / len(expected),
        "macro_f1": sum(float(per_class[label]["f1"]) for label in LABELS)
        / len(LABELS),
        "per_class": per_class,
        "confusion": {
            f"{left}->{right}": confusion[(left, right)]
            for left in LABELS
            for right in LABELS
            if confusion[(left, right)]
        },
    }


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
