"""
Benchmark and Evaluation Harness package for ReconGraph.
"""

from backend.app.benchmark.matcher import (
    AnomalyMatcher,
    extract_detected_issues,
    extract_expected_anomalies,
)
from backend.app.benchmark.metrics import (
    calculate_f1,
    calculate_precision,
    calculate_recall,
    compute_benchmark_metrics,
)
from backend.app.benchmark.models import (
    AnomalyEvaluation,
    AnomalyTypeBenchmarkResult,
    BenchmarkConfig,
    BenchmarkMetrics,
    BenchmarkRunResult,
    DetectedIssue,
    ExpectedAnomaly,
    PerformanceMetrics,
    ScenarioBenchmarkResult,
)
from backend.app.benchmark.reporting import BenchmarkReporter
from backend.app.benchmark.runner import BenchmarkRunner

__all__ = [
    "BenchmarkRunner",
    "BenchmarkReporter",
    "AnomalyMatcher",
    "BenchmarkConfig",
    "BenchmarkRunResult",
    "ScenarioBenchmarkResult",
    "AnomalyTypeBenchmarkResult",
    "BenchmarkMetrics",
    "PerformanceMetrics",
    "ExpectedAnomaly",
    "DetectedIssue",
    "AnomalyEvaluation",
    "calculate_precision",
    "calculate_recall",
    "calculate_f1",
    "compute_benchmark_metrics",
    "extract_detected_issues",
    "extract_expected_anomalies",
]
