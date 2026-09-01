"""
Adjustment domain model.

See docs/data-contracts.md § Adjustment.
"""

from datetime import datetime
from typing import Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class Adjustment(FinancialBaseModel):
    """
    Represents an out-of-band financial adjustment applied to a settlement.
    Covers chargebacks, manual corrections, penalty charges, or balance
    carryovers.

    Primary identifier: adjustment_id

    Note: amount may be negative (debit from merchant) or positive
    (credit to merchant). No enum constraint is applied to `reason`
    because the contract defines it as a free-form string with examples
    rather than an exhaustive finite set.
    """

    # Required
    adjustment_id: str
    merchant_id: str
    amount: MoneyDecimal
    currency: Currency
    reason: str
    created_at: datetime

    # Optional
    settlement_id: Optional[str] = None
    description: Optional[str] = None
