"""
Transfer domain model.

See docs/data-contracts.md § Transfer.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class TransferStatus(str, Enum):
    """Transfer status — per data contract."""
    CREATED = "created"
    PROCESSED = "processed"
    REVERSED = "reversed"
    FAILED = "failed"


class Transfer(FinancialBaseModel):
    """
    Represents a movement of funds from a payment to a linked account
    (Razorpay Route / marketplace model).

    Primary identifier: transfer_id
    """

    # Required
    transfer_id: str
    payment_id: str
    source_merchant_id: str
    recipient_merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    status: TransferStatus
    created_at: datetime

    # Optional
    settlement_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    notes: Optional[Dict[str, str]] = None
