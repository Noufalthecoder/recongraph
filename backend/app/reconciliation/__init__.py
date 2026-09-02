"""
Core deterministic reconciliation engine package for ReconGraph.
"""

from backend.app.reconciliation.engine import DeterministicReconciliationEngine
from backend.app.reconciliation.exceptions import (
    ExceptionSeverity,
    ReconciliationExceptionType,
)
from backend.app.reconciliation.indexer import NormalizedObservationIndex
from backend.app.reconciliation.models import (
    EntityReference,
    ReconciliationConfig,
    ReconciliationEvidence,
    ReconciliationException,
    ReconciliationMatch,
    ReconciliationMetrics,
    ReconciliationResult,
    SettlementReconciliationResult,
    UnmatchedRecord,
)

__all__ = [
    "DeterministicReconciliationEngine",
    "ReconciliationConfig",
    "ReconciliationResult",
    "ReconciliationMatch",
    "ReconciliationException",
    "ReconciliationExceptionType",
    "ExceptionSeverity",
    "EntityReference",
    "ReconciliationEvidence",
    "SettlementReconciliationResult",
    "ReconciliationMetrics",
    "UnmatchedRecord",
    "NormalizedObservationIndex",
]
