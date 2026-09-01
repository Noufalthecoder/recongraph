"""
Refund domain model.

See docs/data-contracts.md § Refund.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class RefundStatus(str, Enum):
    """Refund status — per data contract."""
    CREATED = "created"
    PROCESSED = "processed"
    FAILED = "failed"


class RefundSpeed(str, Enum):
    """Refund speed — per data contract."""
    NORMAL = "normal"
    OPTIMUM = "optimum"


class Refund(FinancialBaseModel):
    """
    Represents a full or partial reversal of a captured payment.

    Primary identifier: refund_id
    """

    # Required
    refund_id: str
    payment_id: str
    merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    status: RefundStatus
    created_at: datetime

    # Optional
    speed: Optional[RefundSpeed] = None
    settlement_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    notes: Optional[Dict[str, str]] = None
