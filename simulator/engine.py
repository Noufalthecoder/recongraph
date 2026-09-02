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
        if scenario == "refund_v1":
            return self._run_refund_v1()
        if scenario == "multiple_refunds_v1":
            return self._run_multiple_refunds_v1()
        if scenario == "adjustment_v1":
            return self._run_adjustment_v1()
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

    def _run_refund_v1(self) -> GroundTruth:
        import decimal
        from simulator.ground_truth.models import SettlementEquation
        from backend.app.models.refund import Refund, RefundStatus, RefundSpeed
        
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        # --- Day 1: Order 1 & Payment 1 ---
        base_time = merchant.created_at + timedelta(hours=1)
        order1_amount = Decimal("10000.00")
        
        order1 = Order(
            order_id=self.generate_id("order_"),
            merchant_id=merchant.merchant_id,
            amount=order1_amount,
            currency=Currency.INR,
            status=OrderStatus.PAID,
            created_at=base_time
        )
        
        pay1_time = base_time + timedelta(minutes=5)
        cap1_time = pay1_time + timedelta(minutes=1)
        
        rounding_str = getattr(self.config, "rounding_mode", "ROUND_HALF_UP")
        rounding = getattr(decimal, rounding_str)
        fee_rate = getattr(self.config, "fee_rate", Decimal("0.02"))
        tax_rate = getattr(self.config, "tax_rate", Decimal("0.18"))
        
        pay1_fee = (order1_amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
        pay1_tax = (pay1_fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
        pay1_net = order1_amount - pay1_fee - pay1_tax
        
        orig_setl_id = self.generate_id("setl_")
        
        payment1 = Payment(
            payment_id=self.generate_id("pay_"),
            order_id=order1.order_id,
            merchant_id=merchant.merchant_id,
            amount=order1_amount,
            currency=Currency.INR,
            status=PaymentStatus.CAPTURED,
            method=PaymentMethod.UPI,
            created_at=pay1_time,
            captured_at=cap1_time,
            fee=pay1_fee,
            tax=pay1_tax,
            settlement_id=orig_setl_id
        )
        
        pay1_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=orig_setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.PAYMENT,
            entity_id=payment1.payment_id,
            amount=order1_amount,
            fee=pay1_fee,
            tax=pay1_tax,
            net_amount=pay1_net,
            type=SettlementTransactionType.CREDIT,
            created_at=cap1_time + timedelta(days=2)
        )
        
        # --- Day 3: Original Settlement S1 ---
        orig_setl_time = payment1.captured_at + timedelta(days=2)
        orig_utr = self.generate_utr()
        
        orig_setl = Settlement(
            settlement_id=orig_setl_id,
            merchant_id=merchant.merchant_id,
            amount=pay1_net,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=pay1_fee,
            tax=pay1_tax,
            created_at=orig_setl_time,
            utr=orig_utr,
            settled_at=orig_setl_time
        )
        
        orig_bank = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=pay1_net,
            currency=Currency.INR,
            utr=orig_utr,
            transaction_date=orig_setl_time + timedelta(days=1),
            description=f"NEFT CR MOCK {orig_setl_id}"
        )
        
        orig_eq = SettlementEquation(
            settlement_id=orig_setl_id,
            expected_amount=pay1_net,
            sum_of_net_amounts=pay1_net,
            total_fees=pay1_fee,
            total_tax=pay1_tax,
            is_balanced=True
        )
        
        orig_label = ScenarioLabel(
            settlement_id=orig_setl_id,
            scenario_type="refund_v1"
        )
        
        # --- Day 4: Order 2 & Payment 2 ---
        order2_time = orig_setl_time + timedelta(days=1)
        order2_amount = Decimal("5000.00")
        
        order2 = Order(
            order_id=self.generate_id("order_"),
            merchant_id=merchant.merchant_id,
            amount=order2_amount,
            currency=Currency.INR,
            status=OrderStatus.PAID,
            created_at=order2_time
        )
        
        pay2_time = order2_time + timedelta(minutes=5)
        cap2_time = pay2_time + timedelta(minutes=1)
        
        pay2_fee = (order2_amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
        pay2_tax = (pay2_fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
        pay2_net = order2_amount - pay2_fee - pay2_tax
        
        ref_setl_id = self.generate_id("setl_")
        
        payment2 = Payment(
            payment_id=self.generate_id("pay_"),
            order_id=order2.order_id,
            merchant_id=merchant.merchant_id,
            amount=order2_amount,
            currency=Currency.INR,
            status=PaymentStatus.CAPTURED,
            method=PaymentMethod.UPI,
            created_at=pay2_time,
            captured_at=cap2_time,
            fee=pay2_fee,
            tax=pay2_tax,
            settlement_id=ref_setl_id
        )
        
        pay2_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=ref_setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.PAYMENT,
            entity_id=payment2.payment_id,
            amount=order2_amount,
            fee=pay2_fee,
            tax=pay2_tax,
            net_amount=pay2_net,
            type=SettlementTransactionType.CREDIT,
            created_at=cap2_time + timedelta(days=2)
        )
        
        # --- Day 4: Refund for Payment 1 ---
        refund_time = order2_time + timedelta(hours=2)
        refund_amount = Decimal("2000.00")
        
        refund = Refund(
            refund_id=self.generate_id("rfnd_"),
            payment_id=payment1.payment_id,
            merchant_id=merchant.merchant_id,
            amount=refund_amount,
            currency=Currency.INR,
            status=RefundStatus.PROCESSED,
            created_at=refund_time,
            processed_at=refund_time + timedelta(minutes=10),
            speed=RefundSpeed.NORMAL,
            settlement_id=ref_setl_id
        )
        
        ref_net_amount = -refund_amount
        
        ref_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=ref_setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.REFUND,
            entity_id=refund.refund_id,
            amount=refund_amount,
            fee=Decimal("0.00"),
            tax=Decimal("0.00"),
            net_amount=ref_net_amount,
            type=SettlementTransactionType.DEBIT,
            created_at=cap2_time + timedelta(days=2)
        )
        
        # --- Day 6: Refund Settlement S2 ---
        ref_setl_time = cap2_time + timedelta(days=2)
        ref_utr = self.generate_utr()
        
        setl2_net = pay2_net + ref_net_amount
        setl2_fee = pay2_fee + Decimal("0.00")
        setl2_tax = pay2_tax + Decimal("0.00")
        
        ref_setl = Settlement(
            settlement_id=ref_setl_id,
            merchant_id=merchant.merchant_id,
            amount=setl2_net,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=setl2_fee,
            tax=setl2_tax,
            created_at=ref_setl_time,
            utr=ref_utr,
            settled_at=ref_setl_time
        )
        
        ref_bank = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=setl2_net,
            currency=Currency.INR,
            utr=ref_utr,
            transaction_date=ref_setl_time + timedelta(days=1),
            description=f"NEFT CR MOCK {ref_setl_id}"
        )
        
        ref_eq = SettlementEquation(
            settlement_id=ref_setl_id,
            expected_amount=setl2_net,
            sum_of_net_amounts=setl2_net,
            total_fees=setl2_fee,
            total_tax=setl2_tax,
            is_balanced=True
        )
        
        ref_label = ScenarioLabel(
            settlement_id=ref_setl_id,
            scenario_type="refund_v1"
        )
        
        gt = GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=[order1, order2],
            payments=[payment1, payment2],
            refunds=[refund],
            settlement_transactions=[pay1_stxn, pay2_stxn, ref_stxn],
            settlements=[orig_setl, ref_setl],
            bank_entries=[orig_bank, ref_bank],
            scenario_labels={orig_setl_id: orig_label, ref_setl_id: ref_label},
            settlement_equations={orig_setl_id: orig_eq, ref_setl_id: ref_eq}
        )
        
        return gt

    def _run_multiple_refunds_v1(self) -> GroundTruth:
        import decimal
        from simulator.ground_truth.models import SettlementEquation
        from backend.app.models.refund import Refund, RefundStatus, RefundSpeed
        
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        rounding_str = getattr(self.config, "rounding_mode", "ROUND_HALF_UP")
        rounding = getattr(decimal, rounding_str)
        fee_rate = getattr(self.config, "fee_rate", Decimal("0.02"))
        tax_rate = getattr(self.config, "tax_rate", Decimal("0.18"))
        
        orders = []
        payments = []
        refunds = []
        stxns = []
        settlements = []
        bank_entries = []
        labels = {}
        equations = {}

        def create_payment_and_settlement(
            day_offset: int,
            payment_amount: Decimal,
            refund_amount: Decimal = Decimal("0.00"),
            refund_against_payment: Payment = None
        ):
            base_time = merchant.created_at + timedelta(days=day_offset - 1, hours=1)
            
            order = Order(
                order_id=self.generate_id("order_"),
                merchant_id=merchant.merchant_id,
                amount=payment_amount,
                currency=Currency.INR,
                status=OrderStatus.PAID,
                created_at=base_time
            )
            orders.append(order)
            
            pay_time = base_time + timedelta(minutes=5)
            cap_time = pay_time + timedelta(minutes=1)
            
            fee = (payment_amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
            tax = (fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
            net_amount = payment_amount - fee - tax
            
            setl_id = self.generate_id("setl_")
            
            payment = Payment(
                payment_id=self.generate_id("pay_"),
                order_id=order.order_id,
                merchant_id=merchant.merchant_id,
                amount=payment_amount,
                currency=Currency.INR,
                status=PaymentStatus.CAPTURED,
                method=PaymentMethod.UPI,
                created_at=pay_time,
                captured_at=cap_time,
                fee=fee,
                tax=tax,
                settlement_id=setl_id
            )
            payments.append(payment)
            
            stxn_time = cap_time + timedelta(days=2)
            pay_stxn = SettlementTransaction(
                settlement_txn_id=self.generate_id("stxn_"),
                settlement_id=setl_id,
                merchant_id=merchant.merchant_id,
                entity_type=SettlementTransactionEntityType.PAYMENT,
                entity_id=payment.payment_id,
                amount=payment_amount,
                fee=fee,
                tax=tax,
                net_amount=net_amount,
                type=SettlementTransactionType.CREDIT,
                created_at=stxn_time
            )
            stxns.append(pay_stxn)
            
            total_net = net_amount
            total_fee = fee
            total_tax = tax
            
            if refund_amount > Decimal("0.00") and refund_against_payment:
                refund_time = base_time + timedelta(hours=2)
                refund = Refund(
                    refund_id=self.generate_id("rfnd_"),
                    payment_id=refund_against_payment.payment_id,
                    merchant_id=merchant.merchant_id,
                    amount=refund_amount,
                    currency=Currency.INR,
                    status=RefundStatus.PROCESSED,
                    created_at=refund_time,
                    processed_at=refund_time + timedelta(minutes=10),
                    speed=RefundSpeed.NORMAL,
                    settlement_id=setl_id
                )
                refunds.append(refund)
                
                ref_net_amount = -refund_amount
                ref_stxn = SettlementTransaction(
                    settlement_txn_id=self.generate_id("stxn_"),
                    settlement_id=setl_id,
                    merchant_id=merchant.merchant_id,
                    entity_type=SettlementTransactionEntityType.REFUND,
                    entity_id=refund.refund_id,
                    amount=refund_amount,
                    fee=Decimal("0.00"),
                    tax=Decimal("0.00"),
                    net_amount=ref_net_amount,
                    type=SettlementTransactionType.DEBIT,
                    created_at=stxn_time
                )
                stxns.append(ref_stxn)
                
                total_net += ref_net_amount

            setl_time = stxn_time
            utr = self.generate_utr()
            
            setl = Settlement(
                settlement_id=setl_id,
                merchant_id=merchant.merchant_id,
                amount=total_net,
                currency=Currency.INR,
                status=SettlementStatus.PROCESSED,
                fees=total_fee,
                tax=total_tax,
                created_at=setl_time,
                utr=utr,
                settled_at=setl_time
            )
            settlements.append(setl)
            
            bank_entry_date = setl_time + timedelta(days=1)
            bank_entry = BankEntry(
                bank_entry_id=self.generate_id("bank_"),
                merchant_id=merchant.merchant_id,
                account_number="ACCT12345678",
                amount=total_net,
                currency=Currency.INR,
                utr=utr,
                transaction_date=bank_entry_date,
                description=f"NEFT CR MOCK {setl_id}"
            )
            bank_entries.append(bank_entry)
            
            labels[setl_id] = ScenarioLabel(
                settlement_id=setl_id,
                scenario_type="multiple_refunds_v1"
            )
            
            equations[setl_id] = SettlementEquation(
                settlement_id=setl_id,
                expected_amount=total_net,
                sum_of_net_amounts=total_net,
                total_fees=total_fee,
                total_tax=total_tax,
                is_balanced=True
            )

            return payment

        p1 = create_payment_and_settlement(day_offset=1, payment_amount=Decimal("10000.00"))
        
        create_payment_and_settlement(
            day_offset=4, 
            payment_amount=Decimal("5000.00"), 
            refund_amount=Decimal("2000.00"), 
            refund_against_payment=p1
        )
        
        create_payment_and_settlement(
            day_offset=7, 
            payment_amount=Decimal("4000.00"), 
            refund_amount=Decimal("1500.00"), 
            refund_against_payment=p1
        )
        
        create_payment_and_settlement(
            day_offset=10, 
            payment_amount=Decimal("3000.00"), 
            refund_amount=Decimal("500.00"), 
            refund_against_payment=p1
        )
        
        return GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=orders,
            payments=payments,
            refunds=refunds,
            settlement_transactions=stxns,
            settlements=settlements,
            bank_entries=bank_entries,
            scenario_labels=labels,
            settlement_equations=equations
        )

    def _run_adjustment_v1(self) -> GroundTruth:
        import decimal
        from simulator.ground_truth.models import SettlementEquation
        from backend.app.models.adjustment import Adjustment
        
        merchant = Merchant(
            merchant_id=self.generate_id("merch_"),
            name="Test Merchant",
            status=MerchantStatus.ACTIVE,
            created_at=datetime.combine(self.config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
        
        rounding_str = getattr(self.config, "rounding_mode", "ROUND_HALF_UP")
        rounding = getattr(decimal, rounding_str)
        fee_rate = getattr(self.config, "fee_rate", Decimal("0.02"))
        tax_rate = getattr(self.config, "tax_rate", Decimal("0.18"))
        
        # Day 1: P1
        p1_amount = Decimal("10000.00")
        p1_time = merchant.created_at + timedelta(hours=1)
        p1_order = Order(
            order_id=self.generate_id("order_"),
            merchant_id=merchant.merchant_id,
            amount=p1_amount,
            currency=Currency.INR,
            status=OrderStatus.PAID,
            created_at=p1_time
        )
        
        p1_fee = (p1_amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
        p1_tax = (p1_fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
        p1_net = p1_amount - p1_fee - p1_tax
        
        setl_id = self.generate_id("setl_")
        
        p1_payment = Payment(
            payment_id=self.generate_id("pay_"),
            order_id=p1_order.order_id,
            merchant_id=merchant.merchant_id,
            amount=p1_amount,
            currency=Currency.INR,
            status=PaymentStatus.CAPTURED,
            method=PaymentMethod.UPI,
            created_at=p1_time + timedelta(minutes=5),
            captured_at=p1_time + timedelta(minutes=6),
            fee=p1_fee,
            tax=p1_tax,
            settlement_id=setl_id
        )
        
        # Ensure STXN dates are identical for aggregation simplicity in this scenario
        stxn_time = p1_payment.captured_at + timedelta(days=4)
        
        p1_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.PAYMENT,
            entity_id=p1_payment.payment_id,
            amount=p1_amount,
            fee=p1_fee,
            tax=p1_tax,
            net_amount=p1_net,
            type=SettlementTransactionType.CREDIT,
            created_at=stxn_time
        )
        
        # Day 2: P2
        p2_amount = Decimal("5000.00")
        p2_time = p1_time + timedelta(days=1)
        p2_order = Order(
            order_id=self.generate_id("order_"),
            merchant_id=merchant.merchant_id,
            amount=p2_amount,
            currency=Currency.INR,
            status=OrderStatus.PAID,
            created_at=p2_time
        )
        
        p2_fee = (p2_amount * fee_rate).quantize(Decimal("0.01"), rounding=rounding)
        p2_tax = (p2_fee * tax_rate).quantize(Decimal("0.01"), rounding=rounding)
        p2_net = p2_amount - p2_fee - p2_tax
        
        p2_payment = Payment(
            payment_id=self.generate_id("pay_"),
            order_id=p2_order.order_id,
            merchant_id=merchant.merchant_id,
            amount=p2_amount,
            currency=Currency.INR,
            status=PaymentStatus.CAPTURED,
            method=PaymentMethod.UPI,
            created_at=p2_time + timedelta(minutes=5),
            captured_at=p2_time + timedelta(minutes=6),
            fee=p2_fee,
            tax=p2_tax,
            settlement_id=setl_id
        )
        
        p2_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.PAYMENT,
            entity_id=p2_payment.payment_id,
            amount=p2_amount,
            fee=p2_fee,
            tax=p2_tax,
            net_amount=p2_net,
            type=SettlementTransactionType.CREDIT,
            created_at=stxn_time
        )
        
        # Day 3: Adjustment A1
        a1_amount = Decimal("-250.00")
        a1_time = p1_time + timedelta(days=2)
        
        a1_adj = Adjustment(
            adjustment_id=self.generate_id("adj_"),
            merchant_id=merchant.merchant_id,
            amount=a1_amount,
            currency=Currency.INR,
            reason="chargeback",
            created_at=a1_time,
            settlement_id=setl_id,
            description="Mock chargeback debit"
        )
        
        a1_stxn = SettlementTransaction(
            settlement_txn_id=self.generate_id("stxn_"),
            settlement_id=setl_id,
            merchant_id=merchant.merchant_id,
            entity_type=SettlementTransactionEntityType.ADJUSTMENT,
            entity_id=a1_adj.adjustment_id,
            amount=abs(a1_amount),
            fee=Decimal("0.00"),
            tax=Decimal("0.00"),
            net_amount=a1_amount,
            type=SettlementTransactionType.DEBIT,
            created_at=stxn_time
        )
        
        # Day 5: Settlement
        stxns = [p1_stxn, p2_stxn, a1_stxn]
        total_net = sum(stxn.net_amount for stxn in stxns)
        total_fee = sum(stxn.fee for stxn in stxns)
        total_tax = sum(stxn.tax for stxn in stxns)
        
        setl_time = stxn_time
        utr = self.generate_utr()
        
        setl = Settlement(
            settlement_id=setl_id,
            merchant_id=merchant.merchant_id,
            amount=total_net,
            currency=Currency.INR,
            status=SettlementStatus.PROCESSED,
            fees=total_fee,
            tax=total_tax,
            created_at=setl_time,
            utr=utr,
            settled_at=setl_time
        )
        
        # Day 6: Bank Entry
        bank_entry_date = setl_time + timedelta(days=1)
        bank_entry = BankEntry(
            bank_entry_id=self.generate_id("bank_"),
            merchant_id=merchant.merchant_id,
            account_number="ACCT12345678",
            amount=setl.amount,
            currency=Currency.INR,
            utr=utr,
            transaction_date=bank_entry_date,
            description=f"NEFT CR MOCK {setl_id}"
        )
        
        label = ScenarioLabel(
            settlement_id=setl_id,
            scenario_type="adjustment_v1"
        )
        
        eq = SettlementEquation(
            settlement_id=setl_id,
            expected_amount=total_net,
            sum_of_net_amounts=total_net,
            total_fees=total_fee,
            total_tax=total_tax,
            is_balanced=True
        )
        
        return GroundTruth(
            config=self.config,
            merchants=[merchant],
            orders=[p1_order, p2_order],
            payments=[p1_payment, p2_payment],
            adjustments=[a1_adj],
            settlement_transactions=[p1_stxn, p2_stxn, a1_stxn],
            settlements=[setl],
            bank_entries=[bank_entry],
            scenario_labels={setl_id: label},
            settlement_equations={setl_id: eq}
        )
