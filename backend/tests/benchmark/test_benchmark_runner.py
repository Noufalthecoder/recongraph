"""
Tests for BenchmarkRunner execution and report generation.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark import BenchmarkConfig, BenchmarkReporter, BenchmarkRunner


def test_runner_clean_only_execution():
    """Verify BenchmarkRunner executes clean scenarios and produces valid report."""
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        scenarios=["minimal_lifecycle_v1", "many_to_one_v1"],
        run_clean=True,
        run_anomalies=False,
    )
    result = runner.run(config)

    assert result.clean_reconciliation_rate == Decimal("1.0000")
    assert len(result.scenario_results) == 2
    assert result.aggregate_metrics.false_positives == 0
    assert result.aggregate_metrics.false_negatives == 0
    assert result.aggregate_metrics.precision == Decimal("1.0000")
    assert result.performance.total_records > 0
    assert result.performance.elapsed_seconds >= 0.0

    # Test reporting outputs
    json_dict = BenchmarkReporter.to_dict(result)
    assert isinstance(json_dict, dict)
    assert json_dict["clean_reconciliation_rate"] == "1.0000"

    text_report = BenchmarkReporter.to_text_report(result)
    assert "RECONGRAPH BENCHMARK REPORT" in text_report
    assert "minimal_lifecycle_v1_clean" in text_report
    assert "Clean Reconciliation Rate: 100.00%" in text_report
