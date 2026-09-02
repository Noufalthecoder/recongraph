"""
Models for the Observed World and Anomaly Injection.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from backend.app.models.merchant import Merchant
from backend.app.models.order import Order
from backend.app.models.payment import Payment
from backend.app.models.refund import Refund
from backend.app.models.adjustment import Adjustment
from backend.app.models.transfer import Transfer
from backend.app.models.settlement_transaction import SettlementTransaction
from backend.app.models.settlement import Settlement
from backend.app.models.bank_entry import BankEntry


class AnomalyType(str, Enum):
    """Supported anomaly types for synthetic injection."""
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_RECORD = "MISSING_RECORD"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    IDENTIFIER_MISMATCH = "IDENTIFIER_MISMATCH"


class AnomalyRecord(BaseModel):
    """
    Immutable audit record describing a single injected anomaly.

    Used strictly for evaluation, benchmarking, and audit trails.
    Must NOT be consumed by the reconciliation engine.
    """
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


class AnomalyManifest(BaseModel):
    """
    Manifest containing all injected anomalies for an ObservedWorld dataset.
    """
    model_config = ConfigDict(frozen=True)

    records: List[AnomalyRecord] = []

    @property
    def total_anomalies(self) -> int:
        return len(self.records)


class ObservedWorld(BaseModel):
    """
    The financial dataset as observed/ingested by the reconciliation system.

    Contains only domain entities and strictly NO anomaly labels or metadata.
    """
    model_config = ConfigDict(frozen=True)

    merchants: List[Merchant]
    orders: List[Order]
    payments: List[Payment]
    refunds: List[Refund] = []
    adjustments: List[Adjustment] = []
    transfers: List[Transfer] = []
    settlement_transactions: List[SettlementTransaction]
    settlements: List[Settlement]
    bank_entries: List[BankEntry]
