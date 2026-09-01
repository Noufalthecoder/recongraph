"""
Settlement domain model.

See docs/data-contracts.md § Settlement.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class SettlementStatus(str, Enum):
    """Settlement status — per data contract."""
    CREATED = "created"
    PROCESSED = "processed"
    FAILED = "failed"


class Settlement(FinancialBaseModel):
    """
    Represents a batch payout from the payment gateway to the merchant's
    bank account. A single settlement aggregates multiple financial
    transactions (payments, refunds, transfers, adjustments) into one
    net amount.

    Primary identifier: settlement_id

    Note: The settlement's amount equals the net sum of all constituent
    SettlementTransaction net_amount values.
    """

    # Required
    settlement_id: str
    merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    status: SettlementStatus
    fees: MoneyDecimal
    tax: MoneyDecimal
    created_at: datetime

    # Optional
    utr: Optional[str] = None
    settled_at: Optional[datetime] = None
