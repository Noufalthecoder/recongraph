"""
Mathematical calculation of benchmark evaluation metrics: Precision, Recall, F1, and rates.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from backend.app.benchmark.models import BenchmarkMetrics


def calculate_precision(tp: int, fp: int, expected_total: int) -> Decimal:
    """
    Computes precision: TP / (TP + FP).

    Zero-case handling:
    - If TP + FP > 0: exact fraction TP / (TP + FP).
    - If TP + FP == 0 and expected_total == 0: 1.0000 (clean dataset with zero false alarms).
    - If TP + FP == 0 and expected_total > 0: 0.0000 (expected anomalies existed but zero were detected).
    """
    if tp + fp > 0:
        return (Decimal(tp) / Decimal(tp + fp)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if expected_total == 0:
        return Decimal("1.0000")
    return Decimal("0.0000")


def calculate_recall(tp: int, fn: int, expected_total: int, fp: int = 0) -> Decimal:
    """
    Computes recall: TP / (TP + FN).

    Zero-case handling:
    - If TP + FN > 0: exact fraction TP / (TP + FN).
    - If TP + FN == 0 and expected_total == 0:
        - If FP == 0: 1.0000 (no anomalies existed, and none were falsely detected).
        - If FP > 0: 0.0000 (false alarms on a clean dataset).
    - If expected_total > 0: 0.0000.
    """
    if tp + fn > 0:
        return (Decimal(tp) / Decimal(tp + fn)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if expected_total == 0:
        return Decimal("1.0000") if fp == 0 else Decimal("0.0000")
    return Decimal("0.0000")


def calculate_f1(precision: Decimal, recall: Decimal) -> Decimal:
    """
    Computes the harmonic mean F1: 2 * Precision * Recall / (Precision + Recall).
    """
    sum_pr = precision + recall
    if sum_pr == Decimal("0.0000") or sum_pr == Decimal("0"):
        return Decimal("0.0000")
    f1_val = (Decimal("2.0") * precision * recall) / sum_pr
    return f1_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def compute_benchmark_metrics(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    total_expected_anomalies: int,
    total_detected_issues: int,
    total_records: int,
    total_settlements: int = 0,
    reconciled_settlements: int = 0,
    exception_settlements: int = 0,
) -> BenchmarkMetrics:
    """
    Assembles authoritative BenchmarkMetrics.
    """
    precision = calculate_precision(true_positives, false_positives, total_expected_anomalies)
    recall = calculate_recall(true_positives, false_negatives, total_expected_anomalies, false_positives)
    f1 = calculate_f1(precision, recall)

    if total_settlements > 0:
        rec_rate = (Decimal(reconciled_settlements) / Decimal(total_settlements)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        exc_rate = (Decimal(exception_settlements) / Decimal(total_settlements)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    else:
        rec_rate = Decimal("1.0000")
        exc_rate = Decimal("0.0000")

    return BenchmarkMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        total_expected_anomalies=total_expected_anomalies,
        total_detected_issues=total_detected_issues,
        total_records=total_records,
        reconciliation_rate=rec_rate,
        exception_rate=exc_rate,
    )
