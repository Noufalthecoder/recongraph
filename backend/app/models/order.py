"""
Order domain model.

See docs/data-contracts.md § Order.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class OrderStatus(str, Enum):
    """Order status — per data contract."""
    CREATED = "created"
    ATTEMPTED = "attempted"
    PAID = "paid"


class Order(FinancialBaseModel):
    """
    Represents a customer's intent to pay.

    Primary identifier: order_id
    """

    # Required
    order_id: str
    merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    status: OrderStatus
    created_at: datetime

    # Optional
    receipt: Optional[str] = None
    notes: Optional[Dict[str, str]] = None
