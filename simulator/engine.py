"""
Simulator engine for minimal lifecycle.
"""

import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from simulator.config import SimulationConfig
from simulator.ground_truth.models import GroundTruth, ScenarioLabel
from backend.app.models.merchant import Merchant, MerchantStatus
from backend.app.models.order import Order, OrderStatus
from backend.app.models.payment import Payment, PaymentStatus, PaymentMethod
from backend.app.models.settlement_transaction import (
    SettlementTransaction,
    SettlementTransactionEntityType,
    SettlementTransactionType,
)
from backend.app.models.settlement import Settlement, SettlementStatus
from backend.app.models.bank_entry import BankEntry
from backend.app.models.common import Currency

class Simulator:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
    
    def generate_id(self, prefix: str) -> str:
        return f"{prefix}{self.rng.randint(100000, 999999)}"

    def generate_utr(self) -> str:
        # Mock UTR
        return f"MOCKUTR{self.rng.randint(100000000, 999999999)}"

    def run(self) -> GroundTruth:
        # Step 5B constraints: exactly one simple valid lifecycle
        
        # 1. Merchant
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        # 2. Order
        amount = Decimal("1000.00")
        order_created_at = merchant.created_at + timedelta(hours=1)
        order = Order(
            order_id=self.generate_id("order_"),
            merchant_id=merchant.merchant_id,
            amount=amount,
            currency=Currency.INR,
            status=OrderStatus.PAID,
            created_at=order_created_at
        )
        
        # 3. Payment
        payment_created_at = order_created_at + timedelta(minutes=5)
        payment_captured_at = payment_created_at + timedelta(minutes=1)
        
        # No fees or tax for this first scenario
        payment = Payment(
            payment_id=self.generate_id("pay_"),
            order_id=order.order_id,
            merchant_id=merchant.merchant_id,
            amount=amount,
            currency=Currency.INR,
            status=PaymentStatus.CAPTURED,
            method=PaymentMethod.UPI,
            created_at=payment_created_at,
            captured_at=payment_captured_at,
            fee=Decimal("0.00"),
            tax=Decimal("0.00")
        )
        
        # 4. Settlement Construction
        settlement_id = self.generate_id("setl_")
        
        # Link payment to settlement
        payment = payment.model_copy(update={"settlement_id": settlement_id})
        
        txn_created_at = payment_captured_at + timedelta(days=2) # T+2
        stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=settlement_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.PAYMENT,
            entity_id=payment.payment_id,
            amount=amount,
            fee=Decimal("0.00"),
            tax=Decimal("0.00"),
            net_amount=amount,
            type=SettlementTransactionType.CREDIT,
            created_at=txn_created_at
        )
        
        # 5. Settlement
        utr = self.generate_utr()
        settlement = Settlement(
            settlement_id=settlement_id,
            merchant_id=merchant.merchant_id,
            amount=amount,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=Decimal("0.00"),
            tax=Decimal("0.00"),
            created_at=txn_created_at,
            utr=utr,
            settled_at=txn_created_at
        )
        
        # 6. BankEntry
        bank_entry_date = txn_created_at + timedelta(days=1)
        bank_entry = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=amount,
            currency=Currency.INR,
            utr=utr,
            transaction_date=bank_entry_date,
            description=f"NEFT CR MOCK {settlement_id}"
        )
        
        # 7. Ground Truth
        label = ScenarioLabel(
            settlement_id=settlement_id,
            scenario_type="minimal_lifecycle_v1"
        )
        
        gt = GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=[order],
            payments=[payment],
            settlement_transactions=[stxn],
            settlements=[settlement],
            bank_entries=[bank_entry],
            scenario_labels={settlement_id: label}
        )
        
        return gt
