"""
Tests for benchmark metric calculations: Precision, Recall, F1, and rate formulas.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark.metrics import (
    calculate_f1,
    calculate_precision,
    calculate_recall,
    compute_benchmark_metrics,
)


def test_perfect_score_metrics():
    """Verify precision, recall, and F1 with 100% true positives and 0 errors."""
    p = calculate_precision(tp=10, fp=0, expected_total=10)
    r = calculate_recall(tp=10, fn=0, expected_total=10, fp=0)
    f1 = calculate_f1(p, r)

    assert p == Decimal("1.0000")
    assert r == Decimal("1.0000")
    assert f1 == Decimal("1.0000")


def test_clean_dataset_zero_anomaly_metrics():
    """Verify zero expected anomalies with zero detections produces 100% precision & recall."""
    p = calculate_precision(tp=0, fp=0, expected_total=0)
    r = calculate_recall(tp=0, fn=0, expected_total=0, fp=0)
    f1 = calculate_f1(p, r)

    assert p == Decimal("1.0000")
    assert r == Decimal("1.0000")
    assert f1 == Decimal("1.0000")


def test_clean_dataset_with_false_positive():
    """Verify false positive on clean dataset drops precision and recall to 0%."""
    p = calculate_precision(tp=0, fp=2, expected_total=0)
    r = calculate_recall(tp=0, fn=0, expected_total=0, fp=2)
    f1 = calculate_f1(p, r)

    assert p == Decimal("0.0000")
    assert r == Decimal("0.0000")
    assert f1 == Decimal("0.0000")


def test_partial_detection_metrics():
    """Verify standard precision/recall/F1 when TP=8, FP=2, FN=2 (Expected=10, Detected=10)."""
    # Precision = 8 / (8 + 2) = 0.8000
    # Recall = 8 / (8 + 2) = 0.8000
    # F1 = 2 * 0.8 * 0.8 / 1.6 = 0.8000
    p = calculate_precision(tp=8, fp=2, expected_total=10)
    r = calculate_recall(tp=8, fn=2, expected_total=10, fp=2)
    f1 = calculate_f1(p, r)

    assert p == Decimal("0.8000")
    assert r == Decimal("0.8000")
    assert f1 == Decimal("0.8000")


def test_zero_detections_when_anomalies_expected():
    """Verify TP=0 when expected=5 results in 0% precision, recall, and F1."""
    p = calculate_precision(tp=0, fp=0, expected_total=5)
    r = calculate_recall(tp=0, fn=5, expected_total=5, fp=0)
    f1 = calculate_f1(p, r)

    assert p == Decimal("0.0000")
    assert r == Decimal("0.0000")
    assert f1 == Decimal("0.0000")


def test_compute_benchmark_metrics_full_model():
    """Verify compute_benchmark_metrics returns fully populated BenchmarkMetrics."""
    metrics = compute_benchmark_metrics(
        true_positives=5,
        false_positives=1,
        false_negatives=0,
        total_expected_anomalies=5,
        total_detected_issues=6,
        total_records=50,
        total_settlements=5,
        reconciled_settlements=4,
        exception_settlements=1,
    )

    # Precision = 5 / 6 = 0.8333
    # Recall = 5 / 5 = 1.0000
    # F1 = 2 * (5/6) * 1 / (11/6) = 10/11 = 0.9091
    assert metrics.true_positives == 5
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0
    assert metrics.precision == Decimal("0.8333")
    assert metrics.recall == Decimal("1.0000")
    assert metrics.f1 == Decimal("0.9091")
    assert metrics.reconciliation_rate == Decimal("0.8000")
    assert metrics.exception_rate == Decimal("0.2000")
