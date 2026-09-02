"""
Tests for the multiple_refunds_v1 financial lifecycle scenario.
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.settlement_transaction import SettlementTransactionType, SettlementTransactionEntityType
from backend.app.models.payment import PaymentStatus

def get_multiple_refunds_v1_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="multiple_refunds_v1",
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP"
    )

def test_multiple_refunds_lifecycle_generation():
    config = get_multiple_refunds_v1_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # 1. Four total Payments exist.
    assert len(gt.payments) == 4
    
    # 2. Exactly three Refunds exist.
    assert len(gt.refunds) == 3
    
    p1 = gt.payments[0]
    p2 = gt.payments[1]
    p3 = gt.payments[2]
    p4 = gt.payments[3]
    
    r1 = gt.refunds[0]
    r2 = gt.refunds[1]
    r3 = gt.refunds[2]
    
    # 3. All three Refunds reference P1.
    assert r1.payment_id == p1.payment_id
    assert r2.payment_id == p1.payment_id
    assert r3.payment_id == p1.payment_id
    
    # 4. Refund IDs are unique.
    assert len({r.refund_id for r in gt.refunds}) == 3
    
    # 5. Refund amounts are positive.
    assert r1.amount > Decimal("0")
    assert r2.amount > Decimal("0")
    assert r3.amount > Decimal("0")
    
    # 6. Total refunded = ₹4,000.
    total_refunded = r1.amount + r2.amount + r3.amount
    assert total_refunded == Decimal("4000.00")
    
    # 7. P1 amount = ₹10,000.
    assert p1.amount == Decimal("10000.00")
    
    # 8. Remaining refundable = ₹6,000.
    remaining_refundable = p1.amount - total_refunded
    assert remaining_refundable == Decimal("6000.00")
    
    # 9. Remaining refundable never becomes negative.
    assert remaining_refundable >= Decimal("0")
    
    # 10. No refund exceeds remaining refundable (logically verified by 6, 7, 8).
    
    # 11. P1 amount remains unchanged.
    assert p1.amount == Decimal("10000.00")
    
    # 12. Every refund has exactly one SettlementTransaction.
    ref_stxns = [stxn for stxn in gt.settlement_transactions if stxn.entity_type == SettlementTransactionEntityType.REFUND]
    assert len(ref_stxns) == 3
    
    # 13. Refund transactions are debit.
    for stxn in ref_stxns:
        assert stxn.type == SettlementTransactionType.DEBIT
        
    # 14. Refund transaction amounts are positive.
    for stxn in ref_stxns:
        assert stxn.amount > Decimal("0")
        
    # 15. Refund net_amount values are negative.
    for stxn in ref_stxns:
        assert stxn.net_amount < Decimal("0")
        
    s1 = gt.settlements[0]
    s2 = gt.settlements[1]
    s3 = gt.settlements[2]
    s4 = gt.settlements[3]
    
    # 16. R1 belongs to S2.
    assert r1.settlement_id == s2.settlement_id
    
    # 17. R2 belongs to S3.
    assert r2.settlement_id == s3.settlement_id
    
    # 18. R3 belongs to S4.
    assert r3.settlement_id == s4.settlement_id
    
    # 19. S2 contains independent Payment P2.
    assert p2.settlement_id == s2.settlement_id
    
    # 20. S3 contains independent Payment P3.
    assert p3.settlement_id == s3.settlement_id
    
    # 21. S4 contains independent Payment P4.
    assert p4.settlement_id == s4.settlement_id
    
    # 22. All Settlement amounts are positive.
    for setl in gt.settlements:
        assert setl.amount > Decimal("0")
        
    # 23. All BankEntry amounts are positive.
    for be in gt.bank_entries:
        assert be.amount > Decimal("0")
        
    # 24. Settlement equation holds exactly.
    for setl in gt.settlements:
        stxns_for_setl = [stxn for stxn in gt.settlement_transactions if stxn.settlement_id == setl.settlement_id]
        total_net = sum(stxn.net_amount for stxn in stxns_for_setl)
        assert setl.amount == total_net
        
    # 25. Ground Truth relationships are correct.
    assert len(gt.settlement_transactions) == 7
    assert len(gt.orders) == 4
    
    # 26. Timeline is chronological.
    assert p1.captured_at < s1.created_at
    assert s1.created_at < p2.captured_at
    assert p2.captured_at < r1.created_at
    assert r1.created_at < s2.created_at
    assert s2.created_at < p3.captured_at
    assert p3.captured_at < r2.created_at
    assert r2.created_at < s3.created_at
    assert s3.created_at < p4.captured_at
    assert p4.captured_at < r3.created_at
    assert r3.created_at < s4.created_at
    
    # 27. All money uses Decimal.
    assert isinstance(p1.amount, Decimal)
    assert isinstance(r1.amount, Decimal)
    assert isinstance(s1.amount, Decimal)

def test_determinism_multiple_refunds_v1():
    # 28. Same seed/config produces identical output.
    gt_a1 = Simulator(get_multiple_refunds_v1_config(42)).run()
    gt_a2 = Simulator(get_multiple_refunds_v1_config(42)).run()
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # 29. Different seed produces different output.
    gt_b = Simulator(get_multiple_refunds_v1_config(99)).run()
    assert gt_a1.model_dump() != gt_b.model_dump()
