"""
Tests for the refund_v1 financial lifecycle scenario.
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.settlement_transaction import SettlementTransactionType, SettlementTransactionEntityType

def get_refund_v1_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="refund_v1",
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP"
    )

def test_refund_lifecycle_generation():
    """Test 1 payment followed by 1 refund."""
    config = get_refund_v1_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # We now have 2 payments and 1 refund
    assert len(gt.payments) == 2
    assert len(gt.refunds) == 1
    
    pay1 = gt.payments[0]
    pay2 = gt.payments[1]
    refund = gt.refunds[0]

    # 1. Refund amount is positive.
    assert refund.amount == Decimal("2000.00")
    
    # 2. Refund SettlementTransaction.amount is positive.
    ref_stxn = gt.settlement_transactions[2]
    assert ref_stxn.entity_type == SettlementTransactionEntityType.REFUND
    assert ref_stxn.amount == Decimal("2000.00")
    
    # 3. Refund SettlementTransaction.type = debit.
    assert ref_stxn.type == SettlementTransactionType.DEBIT
    
    # 4. Refund SettlementTransaction.net_amount is negative.
    assert ref_stxn.net_amount == Decimal("-2000.00")

    # 5. Payment SettlementTransaction.amount is positive.
    pay2_stxn = gt.settlement_transactions[1]
    assert pay2_stxn.entity_type == SettlementTransactionEntityType.PAYMENT
    assert pay2_stxn.amount == Decimal("5000.00")
    
    # 6. Payment SettlementTransaction.net_amount is positive.
    assert pay2_stxn.net_amount > Decimal("0")

    # 7. Original Payment remains unchanged.
    assert pay1.amount == Decimal("10000.00")

    # 8. Original Settlement remains positive.
    orig_setl = gt.settlements[0]
    assert orig_setl.amount > Decimal("0")

    # 9. Refund settlement contains both a payment credit and refund debit.
    # Evaluated by verifying that the setl2 contains both lines
    ref_setl = gt.settlements[1]
    assert pay2_stxn.settlement_id == ref_setl.settlement_id
    assert ref_stxn.settlement_id == ref_setl.settlement_id

    # 10. Refund settlement amount is positive.
    assert ref_setl.amount > Decimal("0")
    
    # 11. BankEntry amount is positive.
    ref_bank = gt.bank_entries[1]
    assert ref_bank.amount > Decimal("0")
    
    # 12. BankEntry amount equals Settlement.amount.
    assert ref_bank.amount == ref_setl.amount
    
    # 13. SUM(transaction.net_amount) equals Settlement.amount.
    assert pay2_stxn.net_amount + ref_stxn.net_amount == ref_setl.amount
    
    # 14. No double-negation occurs (net_amount added directly).
    # 15. No double subtraction occurs (fee/tax computed normally for payment).
    
    # 16. Ground Truth contains both transactions.
    assert len(gt.settlements) == 2
    assert len(gt.settlement_transactions) == 3
    
    # 17. Payment -> Refund relationship is correct.
    assert refund.payment_id == pay1.payment_id
    
    # 18. Refund -> Settlement relationship is correct.
    assert refund.settlement_id == ref_setl.settlement_id

    # 19. Timeline is chronological.
    assert pay1.captured_at < orig_setl.created_at
    assert pay1.captured_at < refund.created_at
    assert pay2.captured_at < ref_setl.created_at
    assert refund.created_at < ref_setl.created_at
    assert ref_setl.created_at < ref_bank.transaction_date

    # 20. All financial values are Decimal.
    assert isinstance(ref_setl.amount, Decimal)
    assert isinstance(ref_stxn.amount, Decimal)
    assert isinstance(ref_stxn.net_amount, Decimal)

def test_determinism_refund_v1():
    """Test same seed produces identical output, different seed produces different."""
    gt_a1 = Simulator(get_refund_v1_config(42)).run()
    gt_a2 = Simulator(get_refund_v1_config(42)).run()
    gt_b = Simulator(get_refund_v1_config(99)).run()

    # 21. Same seed produces identical output
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # 22. Different seed produces different output
    assert gt_a1.model_dump() != gt_b.model_dump()
