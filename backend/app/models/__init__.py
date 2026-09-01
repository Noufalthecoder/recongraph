"""
ReconGraph domain models.

All financial entities defined in docs/data-contracts.md are exported here
for clean import access:

    from backend.app.models import Payment, Settlement, BankEntry
"""

from backend.app.models.common import (
    Currency,
    FinancialBaseModel,
    MoneyDecimal,
)
from backend.app.models.merchant import Merchant, MerchantStatus
from backend.app.models.order import Order, OrderStatus
from backend.app.models.payment import Payment, PaymentMethod, PaymentStatus
from backend.app.models.refund import Refund, RefundSpeed, RefundStatus
from backend.app.models.transfer import Transfer, TransferStatus
from backend.app.models.adjustment import Adjustment
from backend.app.models.settlement_transaction import (
    SettlementTransaction,
    SettlementTransactionEntityType,
    SettlementTransactionType,
)
from backend.app.models.settlement import Settlement, SettlementStatus
from backend.app.models.bank_entry import BankEntry

__all__ = [
    # Base / common
    "Currency",
    "FinancialBaseModel",
    "MoneyDecimal",
    # Entities
    "Merchant",
    "MerchantStatus",
    "Order",
    "OrderStatus",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Refund",
    "RefundSpeed",
    "RefundStatus",
    "Transfer",
    "TransferStatus",
    "Adjustment",
    "SettlementTransaction",
    "SettlementTransactionEntityType",
    "SettlementTransactionType",
    "Settlement",
    "SettlementStatus",
    "BankEntry",
]
