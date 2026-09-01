"""
SettlementTransaction domain model.

See docs/data-contracts.md § SettlementTransaction.
"""

from datetime import datetime
from enum import Enum

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class SettlementTransactionEntityType(str, Enum):
    """Source entity type — per data contract."""
    PAYMENT = "payment"
    REFUND = "refund"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class SettlementTransactionType(str, Enum):
    """Line item direction — per data contract."""
    CREDIT = "credit"
    DEBIT = "debit"


class SettlementTransaction(FinancialBaseModel):
    """
    Represents a single line item within a settlement.

    This is the authoritative record of what was included in a settlement.
    Each SettlementTransaction links exactly one financial entity
    (payment, refund, transfer, or adjustment) to the settlement.

    Primary identifier: settlement_txn_id
    """

    # Required — all fields are required per contract
    settlement_txn_id: str
    settlement_id: str
    merchant_id: str
    entity_type: SettlementTransactionEntityType
    entity_id: str
    amount: MoneyDecimal
    fee: MoneyDecimal
    tax: MoneyDecimal
    net_amount: MoneyDecimal
    type: SettlementTransactionType
    created_at: datetime
