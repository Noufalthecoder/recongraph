"""
Tests for high-volume (>=50 records) large batch reconciliation benchmark.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark import BenchmarkRunner


def test_large_batch_benchmark_100_records():
    """
    Executes a high-volume benchmark dataset with >= 100 financial records,
    evaluating anomaly detection accuracy and performance throughput.
    """
    runner = BenchmarkRunner()
    batch_result = runner.run_large_batch(batch_size=100, seed=42)

    # 1. Total records must be >= 50 (and around 100)
    assert batch_result.total_records >= 50
    assert len(batch_result.expected_anomalies) == 4

    # 2. Verify all injected anomalies in the batch were accurately detected
    assert batch_result.metrics.true_positives == 4
    assert batch_result.metrics.false_negatives == 0
    assert batch_result.metrics.recall == Decimal("1.0000")
    assert batch_result.metrics.f1 >= Decimal("0.8000")
    assert batch_result.reconciliation_status == "EXCEPTION"


def test_large_batch_benchmark_250_records():
    """
    Executes a high-volume benchmark dataset with >= 250 financial records.
    """
    runner = BenchmarkRunner()
    batch_result = runner.run_large_batch(batch_size=250, seed=123)

    assert batch_result.total_records >= 200
    assert batch_result.metrics.true_positives == 4
    assert batch_result.metrics.recall == Decimal("1.0000")
