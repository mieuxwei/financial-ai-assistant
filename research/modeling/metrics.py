from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def binary_classification_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    predicted = (probabilities >= threshold).astype(np.int8)
    tn, fp, fn, tp = (
        int(value)
        for value in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    )
    positives = tp + fn
    negatives = tn + fp
    return {
        "accuracy_supplemental": float(accuracy_score(y_true, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
        "precision_high_risk": float(precision_score(y_true, predicted, zero_division=0)),
        "recall_high_risk": float(recall_score(y_true, predicted, zero_division=0)),
        "f1_high_risk": float(f1_score(y_true, predicted, zero_division=0)),
        "macro_f1": float(f1_score(y_true, predicted, average="macro", zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, predicted)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "false_negative_count": fn,
        "false_negative_rate": float(fn / positives) if positives else None,
        "specificity": float(tn / negatives) if negatives else None,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def uniform_calibration_bins(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    count: int,
) -> list[dict[str, object]]:
    indexes = np.minimum((probabilities * count).astype(int), count - 1)
    bins = []
    for index in range(count):
        mask = indexes == index
        sample_count = int(mask.sum())
        bins.append(
            {
                "lower": index / count,
                "upper": (index + 1) / count,
                "count": sample_count,
                "mean_predicted_probability": (
                    float(probabilities[mask].mean()) if sample_count else None
                ),
                "observed_high_risk_rate": float(y_true[mask].mean()) if sample_count else None,
            }
        )
    return bins
