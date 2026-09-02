"""
Data models for benchmark configuration, expected anomalies, detected issues, and metrics.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.common import MoneyDecimal
from simulator.observed.models import AnomalyType


class BenchmarkConfig(BaseModel):
    """Configuration governing the benchmark execution."""
    model_config = ConfigDict(frozen=True)

    scenarios: List[str] = Field(
        default_factory=lambda: [
            "minimal_lifecycle_v1",
            "many_to_one_v1",
            "many_to_one_with_fee_tax_v1",
            "refund_v1",
            "multiple_refunds_v1",
            "adjustment_v1",
        ]
    )
    anomaly_types: List[AnomalyType] = Field(
        default_factory=lambda: [
            AnomalyType.AMOUNT_MISMATCH,
            AnomalyType.MISSING_RECORD,
            AnomalyType.DUPLICATE_RECORD,
            AnomalyType.IDENTIFIER_MISMATCH,
        ]
    )
    seed: int = 42
    tolerance: MoneyDecimal = Decimal("0.00")
    run_clean: bool = True
    run_anomalies: bool = True
    large_batch_target: int = 100


class ExpectedAnomaly(BaseModel):
    """An anomaly expected from the synthetic AnomalyManifest."""
    model_config = ConfigDict(frozen=True)

    anomaly_id: str
    anomaly_type: AnomalyType
    target_entity_type: str
    target_entity_id: str
    target_field: Optional[str] = None
    original_value: Optional[str] = None
    observed_value: Optional[str] = None
    settlement_id: Optional[str] = None
    description: str


class DetectedIssue(BaseModel):
    """An issue or discrepancy detected by the reconciliation engine."""
    model_config = ConfigDict(frozen=True)

    issue_id: str
    exception_type: str
    severity: str
    entity_type: str
    entity_id: str
    settlement_id: Optional[str] = None
    rule_code: str
    difference: Optional[MoneyDecimal] = None
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AnomalyEvaluation(BaseModel):
    """Comparison between an expected anomaly and a detected reconciliation issue."""
    model_config = ConfigDict(frozen=True)

    anomaly_id: str
    expected_type: AnomalyType
    detected_type: Optional[str] = None
    matched: bool
    match_pass: Optional[str] = None
    expected_entity: str
    detected_entity: Optional[str] = None
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkMetrics(BaseModel):
    """Authoritative precision, recall, F1, and rate metrics."""
    model_config = ConfigDict(frozen=True)

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: Decimal
    recall: Decimal
    f1: Decimal
    total_expected_anomalies: int
    total_detected_issues: int
    total_records: int
    reconciliation_rate: Decimal
    exception_rate: Decimal


class ScenarioBenchmarkResult(BaseModel):
    """Benchmark outcome for a single scenario run."""
    model_config = ConfigDict(frozen=True)

    scenario_name: str
    is_clean: bool
    total_records: int
    settlement_count: int
    expected_anomalies: List[ExpectedAnomaly] = Field(default_factory=list)
    detected_issues: List[DetectedIssue] = Field(default_factory=list)
    evaluations: List[AnomalyEvaluation] = Field(default_factory=list)
    metrics: BenchmarkMetrics
    reconciliation_status: str


class AnomalyTypeBenchmarkResult(BaseModel):
    """Benchmark breakdown for a specific anomaly type."""
    model_config = ConfigDict(frozen=True)

    anomaly_type: str
    expected_count: int
    detected_count: int
    tp: int
    fp: int
    fn: int
    precision: Decimal
    recall: Decimal
    f1: Decimal


class PerformanceMetrics(BaseModel):
    """Measured execution performance."""
    model_config = ConfigDict(frozen=True)

    elapsed_seconds: float
    total_records: int
    records_per_second: float


class BenchmarkRunResult(BaseModel):
    """Top-level immutable outcome of an entire benchmark evaluation run."""
    model_config = ConfigDict(frozen=True)

    run_id: str
    config: BenchmarkConfig
    scenario_results: List[ScenarioBenchmarkResult]
    anomaly_breakdown: Dict[str, AnomalyTypeBenchmarkResult]
    aggregate_metrics: BenchmarkMetrics
    performance: PerformanceMetrics
    clean_reconciliation_rate: Decimal
