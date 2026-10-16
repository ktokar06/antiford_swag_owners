"""Порог по validation; test используется только для окончательной оценки."""
import numpy as np
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    log_loss, precision_score, recall_score, roc_auc_score,
)


def ratings(probabilities):
    return np.clip(np.rint(np.asarray(probabilities) * 100), 0, 100).astype(int)


def choose_threshold(y, probabilities, max_fpr, review_threshold):
    y, scores = np.asarray(y, dtype=int), ratings(probabilities)
    if set(y) != {0, 1}:
        raise ValueError("Validation должен содержать и фрод, и легитимные вызовы")
    # 101 означает: ни один балл 0..100 не допускает автоблокировку.
    for threshold in range(review_threshold + 1, 102):
        if ((scores >= threshold) & (y == 0)).sum() / (y == 0).sum() <= max_fpr:
            return threshold
    return 101


def evaluate(y, probabilities, threshold, scenarios=None):
    y, probabilities = np.asarray(y, dtype=int), np.asarray(probabilities)
    predicted = ratings(probabilities) >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    result = {
        "rows": len(y), "fraud_rows": int(y.sum()), "threshold": threshold,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "pr_auc": float(average_precision_score(y, probabilities)) if len(set(y)) == 2 else None,
        "roc_auc": float(roc_auc_score(y, probabilities)) if len(set(y)) == 2 else None,
        "brier_score": float(brier_score_loss(y, probabilities)),
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
    }
    if scenarios is not None:
        scenarios = np.asarray(scenarios.fillna("unspecified").astype(str))
        result["by_scenario"] = {
            str(name): evaluate(y[scenarios == name], probabilities[scenarios == name], threshold)
            for name in sorted(set(scenarios))
        }
    return result
