"""
BankEntry domain model.

See docs/data-contracts.md § BankEntry.
"""

from datetime import datetime
from typing import Optional

from backend.app.models.common import Currency, FinancialBaseModel, MoneyDecimal


class BankEntry(FinancialBaseModel):
    """
    Represents a single credit entry in the merchant's bank statement.

    This is the external, bank-side record of money received.
    BankEntries are matched to Settlements via the UTR
    (Unique Transaction Reference).

    Primary identifier: bank_entry_id

    Note: The Settlement ↔ BankEntry relationship is established by
    matching Settlement.utr = BankEntry.utr. There is no direct
    foreign key.
    """

    # Required
    bank_entry_id: str
    merchant_id: str
    account_number: str
    amount: MoneyDecimal
    currency: Currency
    utr: str
    transaction_date: datetime

    # Optional
    description: Optional[str] = None
    value_date: Optional[datetime] = None
    balance: Optional[MoneyDecimal] = None
