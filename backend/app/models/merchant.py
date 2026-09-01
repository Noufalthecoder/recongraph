"""
Merchant domain model.

See docs/data-contracts.md § Merchant.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from backend.app.models.common import FinancialBaseModel


class MerchantStatus(str, Enum):
    """Merchant account status — per data contract."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class Merchant(FinancialBaseModel):
    """
    Represents a business entity that accepts payments through the
    payment gateway.

    Primary identifier: merchant_id
    """

    # Required
    merchant_id: str
    name: str
    status: MerchantStatus
    created_at: datetime

    # Optional
    mcc: Optional[str] = None
    settlement_schedule: Optional[str] = None
    fee_plan_id: Optional[str] = None
