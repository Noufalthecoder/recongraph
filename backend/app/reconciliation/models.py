"""
Data models for deterministic reconciliation results, matches, exceptions, and metrics.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.common import MoneyDecimal
from backend.app.reconciliation.exceptions import ExceptionSeverity, ReconciliationExceptionType


class EntityReference(BaseModel):
    """Immutable identifier reference for an entity in the financial graph."""
    model_config = ConfigDict(frozen=True)

    entity_type: str
    entity_id: str


class ReconciliationEvidence(BaseModel):
    """
    Deterministic mathematical and audit proof for a reconciliation decision.
    """
    model_config = ConfigDict(frozen=True)

    rule_code: str
    rule_description: str
    primary_entity: EntityReference
    related_entities: List[EntityReference] = Field(default_factory=list)
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    difference: Optional[MoneyDecimal] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ReconciliationMatch(BaseModel):
    """
    Record of a successfully reconciled entity relationship.
    """
    model_config = ConfigDict(frozen=True)

    match_id: str
    match_type: str
    entities: List[EntityReference]
    evidence: ReconciliationEvidence


class ReconciliationException(BaseModel):
    """
    Record of an identified discrepancy, broken rule, or ledger imbalance.
    """
    model_config = ConfigDict(frozen=True)

    exception_id: str
    exception_type: ReconciliationExceptionType
    severity: ExceptionSeverity
    primary_entity: EntityReference
    related_entities: List[EntityReference] = Field(default_factory=list)
    rule_code: str
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    difference: Optional[MoneyDecimal] = None
    evidence: ReconciliationEvidence


class UnmatchedRecord(BaseModel):
    """
    Record that has no corresponding matching counterparty or settlement participation.
    """
    model_config = ConfigDict(frozen=True)

    entity: EntityReference
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SettlementReconciliationResult(BaseModel):
    """
    Per-settlement batch reconciliation breakdown.
    """
    model_config = ConfigDict(frozen=True)

    settlement_id: str
    merchant_id: str
    status: str  # "RECONCILED", "EXCEPTION", "UNMATCHED"
    settlement_amount: MoneyDecimal
    calculated_component_total: MoneyDecimal
    difference: MoneyDecimal
    bank_entry_id: Optional[str] = None
    utr: Optional[str] = None
    line_item_count: int
    matches: List[ReconciliationMatch] = Field(default_factory=list)
    exceptions: List[ReconciliationException] = Field(default_factory=list)


class ReconciliationMetrics(BaseModel):
    """
    Aggregate metrics computed over the reconciliation run.
    """
    model_config = ConfigDict(frozen=True)

    total_records: int
    total_merchants: int
    total_orders: int
    total_payments: int
    total_refunds: int
    total_adjustments: int
    total_settlement_transactions: int
    total_settlements: int
    total_bank_entries: int

    reconciled_settlements_count: int
    exception_settlements_count: int
    unmatched_settlements_count: int
    unmatched_bank_entries_count: int

    total_matches_count: int
    total_exceptions_count: int
    total_unmatched_count: int

    settlement_reconciliation_rate: Decimal
    processing_time_ms: float


class ReconciliationConfig(BaseModel):
    """
    Configuration parameters for deterministic reconciliation.
    """
    model_config = ConfigDict(frozen=True)

    tolerance: MoneyDecimal = Field(
        default=Decimal("0.00"),
        description="Allowed difference for monetary matches (default: ₹0.00 exact)."
    )
    validate_component_fees_tax: bool = Field(
        default=True,
        description="Whether to validate SettlementTransaction net_amount = amount - fee - tax."
    )
    allow_orphan_records: bool = Field(
        default=True,
        description="Whether orphan payments/bank entries are treated as UNMATCHED rather than fatal exceptions."
    )


class ReconciliationResult(BaseModel):
    """
    Top-level immutable outcome of a deterministic reconciliation run.
    """
    model_config = ConfigDict(frozen=True)

    run_id: str
    status: str  # "RECONCILED", "EXCEPTION", "PARTIALLY_RECONCILED", "UNMATCHED"
    config: ReconciliationConfig
    summary: str
    settlements: List[SettlementReconciliationResult]
    matches: List[ReconciliationMatch]
    exceptions: List[ReconciliationException]
    unmatched: List[UnmatchedRecord]
    metrics: ReconciliationMetrics
