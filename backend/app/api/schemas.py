"""
Pydantic API request and response schemas for ReconGraph.
Ensures Decimal money values are serialized strictly as exact strings.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str
    service: str


class DashboardKPIs(BaseModel):
    model_config = ConfigDict(frozen=True)
    active_scenario: str
    active_scenario_label: str
    total_records: int
    settlement_count: int
    reconciled_count: int
    exception_count: int
    unmatched_count: int
    reconciliation_rate: str
    total_settlement_value: str
    total_bank_value: str
    benchmark_f1: str
    benchmark_precision: str
    benchmark_recall: str
    benchmark_clean_rate: str
    throughput_display: str


class ExceptionSummaryItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    exception_id: str
    rule_code: str
    severity: str
    entity_type: str
    entity_id: str
    settlement_id: Optional[str] = None
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    difference: Optional[str] = None
    description: str


class DashboardResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    kpis: DashboardKPIs
    settlement_health: Dict[str, int]
    exception_distribution: Dict[str, int]
    recent_exceptions: List[ExceptionSummaryItem]


class ScenarioInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    scenario_id: str
    name: str
    description: str
    record_count: int
    has_anomalies: bool
    is_active: bool


class ScenarioListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    scenarios: List[ScenarioInfo]
    active_scenario_id: str


class SettlementListItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    settlement_id: str
    utr: str
    amount: str
    currency: str
    status: str
    bank_amount: Optional[str] = None
    difference: Optional[str] = None
    exception_count: int
    transaction_count: int
    created_at: str


class SettlementListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    settlements: List[SettlementListItem]
    total_count: int


class FinancialEquationComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    type: str  # payment, refund, adjustment, fee, tax, bank
    amount: str
    count: int
    sign: str  # "+", "-", "="


class SettlementDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    settlement_id: str
    merchant_id: str
    utr: str
    amount: str
    fees: str
    tax: str
    currency: str
    status: str
    created_at: str
    bank_entry: Optional[Dict[str, Any]] = None
    equation_components: List[FinancialEquationComponent]
    exceptions: List[ExceptionSummaryItem]
    evidence: List[Dict[str, Any]]
    constituent_transactions: List[Dict[str, Any]]
    payments: List[Dict[str, Any]]
    refunds: List[Dict[str, Any]]
    adjustments: List[Dict[str, Any]]


class GraphNodeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    node_id: str
    entity_type: str
    entity_id: str
    display_label: str
    status: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    edge_id: str
    source: str
    target: str
    relationship_type: str
    directed: bool = True
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    nodes: List[GraphNodeDTO]
    edges: List[GraphEdgeDTO]
    total_nodes: int
    total_edges: int


class InvestigationRequestDTO(BaseModel):
    question: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None


class InvestigationResponseDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    question: str
    status: str
    confidence: str
    answer: str
    finding: str
    evidence: List[Dict[str, Any]]
    citations: List[str]
    affected_records: List[str]
    financial_breakdown: Dict[str, Any]
    recommended_next_check: List[str]
    suggested_next_steps: List[str]
    tool_calls: List[Dict[str, Any]]


class BenchmarkAnomalyRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    anomaly_type: str
    expected_count: int
    detected_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: str
    recall: str
    f1: str


class BenchmarkResponseDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_records_processed: int
    total_scenarios_evaluated: int
    total_expected_anomalies: int
    total_detected_issues: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: str
    recall: str
    f1: str
    clean_reconciliation_rate: str
    records_per_second: str
    elapsed_seconds: str
    anomaly_breakdown: List[BenchmarkAnomalyRow]
    isolation_note: str
