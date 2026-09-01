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
        scenario = getattr(self.config, "scenario_type", "minimal_lifecycle_v1")
        if scenario == "many_to_one_with_fee_tax_v1":
            return self._run_many_to_one_with_fee_tax()
        if scenario == "many_to_one_v1":
            return self._run_many_to_one()
        return self._run_minimal_lifecycle()

    def _run_minimal_lifecycle(self) -> GroundTruth:
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

    def _run_many_to_one(self) -> GroundTruth:
        # Step 5C constraints: 5 orders, 5 payments -> 1 settlement
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        orders = []
        payments = []
        stxns = []
        
        settlement_id = self.generate_id("setl_")
        total_amount = Decimal("0.00")
        amounts = [Decimal("1250.00"), Decimal("3400.00"), Decimal("850.00"), Decimal("2100.00"), Decimal("5600.00")]
        base_time = merchant.created_at + timedelta(hours=1)
        
        for i in range(5):
            amount = amounts[i]
            total_amount += amount
            
            order_time = base_time + timedelta(hours=i)
            order = Order(
                order_id=self.generate_id("order_"),
                merchant_id=merchant.merchant_id,
                amount=amount,
                currency=Currency.INR,
                status=OrderStatus.PAID,
                created_at=order_time
            )
            orders.append(order)
            
            payment_time = order_time + timedelta(minutes=5)
            capture_time = payment_time + timedelta(minutes=1)
            payment = Payment(
                payment_id=self.generate_id("pay_"),
                order_id=order.order_id,
                merchant_id=merchant.merchant_id,
                amount=amount,
                currency=Currency.INR,
                status=PaymentStatus.CAPTURED,
                method=PaymentMethod.UPI,
                created_at=payment_time,
                captured_at=capture_time,
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                settlement_id=settlement_id
            )
            payments.append(payment)
            
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
                created_at=capture_time + timedelta(days=2)
            )
            stxns.append(stxn)
            
        txn_created_at = payments[-1].captured_at + timedelta(days=2)
        utr = self.generate_utr()
        
        settlement = Settlement(
            settlement_id=settlement_id,
            merchant_id=merchant.merchant_id,
            amount=total_amount,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=Decimal("0.00"),
            tax=Decimal("0.00"),
            created_at=txn_created_at,
            utr=utr,
            settled_at=txn_created_at
        )
        
        bank_entry_date = txn_created_at + timedelta(days=1)
        bank_entry = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=total_amount,
            currency=Currency.INR,
            utr=utr,
            transaction_date=bank_entry_date,
            description=f"NEFT CR MOCK {settlement_id}"
        )
        
        label = ScenarioLabel(
            settlement_id=settlement_id,
            scenario_type="many_to_one_v1"
        )
        
        gt = GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=orders,
            payments=payments,
            settlement_transactions=stxns,
            settlements=[settlement],
            bank_entries=[bank_entry],
            scenario_labels={settlement_id: label}
        )
        
        return gt

    def _run_many_to_one_with_fee_tax(self) -> GroundTruth:
        import decimal
        from simulator.ground_truth.models import SettlementEquation
        
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        orders = []
        payments = []
        stxns = []
        
        settlement_id = self.generate_id("setl_")
        total_gross = Decimal("0.00")
        total_fee = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_net = Decimal("0.00")
        
        amounts = [Decimal("1250.00"), Decimal("3400.00"), Decimal("850.00"), Decimal("2100.00"), Decimal("5600.00")]
        base_time = merchant.created_at + timedelta(hours=1)
        
        rounding_str = getattr(self.config, "rounding_mode", "ROUND_HALF_UP")
        rounding = getattr(decimal, rounding_str)
        fee_rate = getattr(self.config, "fee_rate", Decimal("0.02"))
        tax_rate = getattr(self.config, "tax_rate", Decimal("0.18"))
        
        for i in range(5):
            amount = amounts[i]
            
            fee = (amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
            tax = (fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
            net_amount = amount - fee - tax
            
            total_gross += amount
            total_fee += fee
            total_tax += tax
            total_net += net_amount
            
            order_time = base_time + timedelta(hours=i)
            order = Order(
                order_id=self.generate_id("order_"),
                merchant_id=merchant.merchant_id,
                amount=amount,
                currency=Currency.INR,
                status=OrderStatus.PAID,
                created_at=order_time
            )
            orders.append(order)
            
            payment_time = order_time + timedelta(minutes=5)
            capture_time = payment_time + timedelta(minutes=1)
            payment = Payment(
                payment_id=self.generate_id("pay_"),
                order_id=order.order_id,
                merchant_id=merchant.merchant_id,
                amount=amount,
                currency=Currency.INR,
                status=PaymentStatus.CAPTURED,
                method=PaymentMethod.UPI,
                created_at=payment_time,
                captured_at=capture_time,
                fee=fee,
                tax=tax,
                settlement_id=settlement_id
            )
            payments.append(payment)
            
            stxn = SettlementTransaction(
                settlement_txn_id=self.generate_id("stxn_"),
                settlement_id=settlement_id,
                merchant_id=merchant.merchant_id,
                entity_type=SettlementTransactionEntityType.PAYMENT,
                entity_id=payment.payment_id,
                amount=amount,
                fee=fee,
                tax=tax,
                net_amount=net_amount,
                type=SettlementTransactionType.CREDIT,
                created_at=capture_time + timedelta(days=2)
            )
            stxns.append(stxn)
            
        txn_created_at = payments[-1].captured_at + timedelta(days=2)
        utr = self.generate_utr()
        
        settlement = Settlement(
            settlement_id=settlement_id,
            merchant_id=merchant.merchant_id,
            amount=total_net,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=total_fee,
            tax=total_tax,
            created_at=txn_created_at,
            utr=utr,
            settled_at=txn_created_at
        )
        
        bank_entry_date = txn_created_at + timedelta(days=1)
        bank_entry = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=total_net,
            currency=Currency.INR,
            utr=utr,
            transaction_date=bank_entry_date,
            description=f"NEFT CR MOCK {settlement_id}"
        )
        
        label = ScenarioLabel(
            settlement_id=settlement_id,
            scenario_type="many_to_one_with_fee_tax_v1"
        )
        
        eq = SettlementEquation(
            settlement_id=settlement_id,
            expected_amount=total_net,
            sum_of_net_amounts=total_net,
            total_fees=total_fee,
            total_tax=total_tax,
            is_balanced=True
        )
        
        gt = GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=orders,
            payments=payments,
            settlement_transactions=stxns,
            settlements=[settlement],
            bank_entries=[bank_entry],
            scenario_labels={settlement_id: label},
            settlement_equations={settlement_id: eq}
        )
        
        return gt
