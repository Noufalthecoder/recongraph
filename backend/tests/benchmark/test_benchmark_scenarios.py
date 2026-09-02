"""
Tests evaluating the benchmark across all 6 supported scenarios in clean and anomaly-injected modes.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark import BenchmarkConfig, BenchmarkRunner
from simulator.observed.models import AnomalyType


def test_full_benchmark_run_across_all_six_scenarios():
    """
    Executes a complete benchmark run across all 6 scenarios in both clean and anomaly modes.
    Verifies 100% clean reconciliation rate and accurate anomaly detection.
    """
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        scenarios=[
            "minimal_lifecycle_v1",
            "many_to_one_v1",
            "many_to_one_with_fee_tax_v1",
            "refund_v1",
            "multiple_refunds_v1",
            "adjustment_v1",
        ],
        run_clean=True,
        run_anomalies=True,
    )
    result = runner.run(config)

    # 1. 6 clean scenarios + 24 anomaly scenarios (6 scenarios * 4 anomaly types) = 30 total scenario evaluations
    assert len(result.scenario_results) == 30

    # 2. Clean reconciliation rate must be 100%
    assert result.clean_reconciliation_rate == Decimal("1.0000")

    # 3. Verify clean runs have 0 false positives
    clean_runs = [s for s in result.scenario_results if s.is_clean]
    assert len(clean_runs) == 6
    for c in clean_runs:
        assert c.reconciliation_status == "RECONCILED"
        assert c.metrics.false_positives == 0
        assert c.metrics.false_negatives == 0
        assert c.metrics.true_positives == 0
        assert c.metrics.precision == Decimal("1.0000")

    # 4. Verify anomaly breakdown contains all 4 types with high precision and recall
    for anom_type in [
        AnomalyType.AMOUNT_MISMATCH.value,
        AnomalyType.MISSING_RECORD.value,
        AnomalyType.DUPLICATE_RECORD.value,
        AnomalyType.IDENTIFIER_MISMATCH.value,
    ]:
        assert anom_type in result.anomaly_breakdown
        breakdown = result.anomaly_breakdown[anom_type]
        assert breakdown.expected_count == 6
        assert breakdown.tp >= 5
        assert breakdown.precision >= Decimal("0.8000")
        assert breakdown.recall >= Decimal("0.8000")
        assert breakdown.f1 >= Decimal("0.8000")

    # 5. Overall aggregate metrics sanity
    agg = result.aggregate_metrics
    assert agg.true_positives >= 20
    assert agg.precision >= Decimal("0.8500")
    assert agg.recall >= Decimal("0.8500")
    assert agg.f1 >= Decimal("0.8500")
