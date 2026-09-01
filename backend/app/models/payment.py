"""
Payment domain model.

See docs/data-contracts.md § Payment.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class PaymentStatus(str, Enum):
    """Payment status — per data contract."""
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method — per data contract."""
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"
    EMI = "emi"


class Payment(FinancialBaseModel):
    """
    Represents a single payment attempt against an order.

    Primary identifier: payment_id

    Note: settlement_id is a denormalized convenience field.
    The authoritative settlement linkage is through SettlementTransaction.
    """

    # Required
    payment_id: str
    order_id: str
    merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    status: PaymentStatus
    method: PaymentMethod
    created_at: datetime

    # Optional
    fee: Optional[MoneyDecimal] = None
    tax: Optional[MoneyDecimal] = None
    settlement_id: Optional[str] = None
    captured_at: Optional[datetime] = None
    notes: Optional[Dict[str, str]] = None
