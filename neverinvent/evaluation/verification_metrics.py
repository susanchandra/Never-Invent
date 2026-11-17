"""
evaluation/verification_metrics.py — Evaluation metrics for claim verification.

Metrics implemented:
- Fabrication Detection Precision: TP / (TP + FP) where positive = predicted UNSUPPORTED
- Fabrication Detection Recall: TP / Total Fabricated Expected UNSUPPORTED
- F1 Score: 2 * (P * R) / (P + R)
- False Block Rate: Fraction of faithful claims wrongly marked UNSUPPORTED
- Ambiguity Rate: Fraction of all claims marked AMBIGUOUS (requiring human review)
- Confusion Matrix: 3x3 matrix across SUPPORTED, UNSUPPORTED, AMBIGUOUS
- Per-Category Metrics: Metric breakdown per fabrication category
- Latency Statistics: mean, p50, p95, min, max
"""

from __future__ import annotations

import numpy as np
from typing import Any

from neverinvent.evaluation.fabrication_dataset import FabricationCase
from neverinvent.verification.models import Verdict, VerificationResult


def compute_confusion_matrix(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> dict[str, dict[str, int]]:
    """
    Computes a 3x3 confusion matrix: actual (expected) vs predicted verdict.
    """
    labels = [Verdict.SUPPORTED.value, Verdict.UNSUPPORTED.value, Verdict.AMBIGUOUS.value]
    matrix = {act: {pred: 0 for pred in labels} for act in labels}

    for res, case in zip(results, cases):
        act = case.expected_verdict.value
        pred = res.final_verdict.value
        matrix[act][pred] += 1

    return matrix


def fabrication_detection_precision(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> float:
    """
    Precision: TP / (TP + FP)
    Positive prediction = UNSUPPORTED.
    TP = predicted UNSUPPORTED and actually fabricated.
    FP = predicted UNSUPPORTED but actually faithful.
    """
    tp = 0
    fp = 0
    for res, case in zip(results, cases):
        if res.final_verdict == Verdict.UNSUPPORTED:
            if case.is_fabricated:
                tp += 1
            else:
                fp += 1

    if tp + fp == 0:
        return 1.0
    return float(tp / (tp + fp))


def fabrication_detection_recall(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> float:
    """
    Recall: TP / Total Fabrications with expected verdict UNSUPPORTED.
    """
    tp = 0
    total_unsupported_expected = 0
    for res, case in zip(results, cases):
        if case.expected_verdict == Verdict.UNSUPPORTED:
            total_unsupported_expected += 1
            if res.final_verdict == Verdict.UNSUPPORTED:
                tp += 1

    if total_unsupported_expected == 0:
        return 1.0
    return float(tp / total_unsupported_expected)


def f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return float(2.0 * (precision * recall) / (precision + recall))


def false_block_rate(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> float:
    """
    False Block Rate: Faithful claims wrongly classified as UNSUPPORTED / Total Faithful Claims.
    """
    faithful_total = 0
    false_blocks = 0
    for res, case in zip(results, cases):
        if not case.is_fabricated:
            faithful_total += 1
            if res.final_verdict == Verdict.UNSUPPORTED:
                false_blocks += 1

    if faithful_total == 0:
        return 0.0
    return float(false_blocks / faithful_total)


def ambiguity_rate(results: list[VerificationResult]) -> float:
    """
    Fraction of claims marked AMBIGUOUS (escalated to human review).
    """
    if not results:
        return 0.0
    amb_count = sum(1 for r in results if r.final_verdict == Verdict.AMBIGUOUS)
    return float(amb_count / len(results))


def compute_three_class_metrics(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> dict[str, dict[str, float]]:
    """
    Computes per-class precision, recall, F1, and support across
    SUPPORTED, UNSUPPORTED, and AMBIGUOUS, along with Macro averages.
    """
    labels = [Verdict.SUPPORTED.value, Verdict.UNSUPPORTED.value, Verdict.AMBIGUOUS.value]
    metrics: dict[str, dict[str, float]] = {}

    for label in labels:
        tp = sum(
            1
            for r, c in zip(results, cases)
            if r.final_verdict.value == label and c.expected_verdict.value == label
        )
        fp = sum(
            1
            for r, c in zip(results, cases)
            if r.final_verdict.value == label and c.expected_verdict.value != label
        )
        fn = sum(
            1
            for r, c in zip(results, cases)
            if r.final_verdict.value != label and c.expected_verdict.value == label
        )
        support = sum(1 for c in cases if c.expected_verdict.value == label)

        p = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        r = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2.0 * (p * r) / (p + r)) if (p + r) > 0 else 0.0

        metrics[label] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    macro_p = float(np.mean([metrics[l]["precision"] for l in labels]))
    macro_r = float(np.mean([metrics[l]["recall"] for l in labels]))
    macro_f1 = float(np.mean([metrics[l]["f1"] for l in labels]))

    metrics["macro_average"] = {
        "precision": round(macro_p, 4),
        "recall": round(macro_r, 4),
        "f1": round(macro_f1, 4),
        "support": len(cases),
    }

    return metrics


def compute_latency_stats(results: list[VerificationResult]) -> dict[str, float]:
    """Computes mean, p50, p95, min, and max latency in milliseconds."""
    latencies = [r.latency_ms for r in results]
    if not latencies:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}

    return {
        "mean_ms": float(np.mean(latencies)),
        "p50_ms": float(np.percentile(latencies, 50)),
        "p95_ms": float(np.percentile(latencies, 95)),
        "min_ms": float(np.min(latencies)),
        "max_ms": float(np.max(latencies)),
    }


def compute_per_category_metrics(
    results: list[VerificationResult], cases: list[FabricationCase]
) -> dict[str, dict[str, Any]]:
    """
    Computes per-category accuracy, precision, recall, and count breakdown.
    """
    categories: dict[str, list[tuple[VerificationResult, FabricationCase]]] = {}
    for r, c in zip(results, cases):
        categories.setdefault(c.fabrication_type, []).append((r, c))

    per_cat: dict[str, dict[str, Any]] = {}
    for cat, items in categories.items():
        cat_results = [item[0] for item in items]
        cat_cases = [item[1] for item in items]

        correct = sum(
            1 for r, c in zip(cat_results, cat_cases) if r.final_verdict == c.expected_verdict
        )
        total = len(items)
        accuracy = correct / total if total > 0 else 0.0
        p = fabrication_detection_precision(cat_results, cat_cases)
        r = fabrication_detection_recall(cat_results, cat_cases)
        f1 = f1_score(p, r)

        per_cat[cat] = {
            "total_cases": total,
            "correct_verdicts": correct,
            "accuracy": round(accuracy, 4),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
        }

    return per_cat
