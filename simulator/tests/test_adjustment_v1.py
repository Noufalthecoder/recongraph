"""
Tests for the adjustment_v1 financial lifecycle scenario.
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.settlement_transaction import (
    SettlementTransactionType,
    SettlementTransactionEntityType,
)
from backend.app.models.payment import PaymentStatus
from backend.app.models.order import OrderStatus
from backend.app.models.settlement import SettlementStatus


def get_adjustment_v1_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="adjustment_v1",
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP",
    )


def test_adjustment_lifecycle_generation():
    """
    Validates complete lifecycle and all 14 invariants for adjustment_v1:
    - A. Scenario generation succeeds.
    - B. Entity counts: 2 Orders, 2 Payments, 1 Adjustment, 3 STXNs, 1 Settlement, 1 BankEntry.
    - C. Payment P1 calculation: gross=10000, fee=200, tax=36, net=9764.
    - D. Payment P2 calculation: gross=5000, fee=100, tax=18, net=4882.
    - E. Adjustment: amount=250 (signed -250.00), direction=debit.
    - F. Adjustment STXN: type=debit, net_amount=-250, amount=250, fee=0, tax=0.
    - G. Settlement equation: 9764 + 4882 - 250 = 14396.
    - H. Settlement amount: 14396.
    - I. BankEntry amount: 14396.
    - J. BankEntry is positive (> 0).
    - K. Ground Truth contains all expected relationships and timeline.
    """
    # A. Scenario generation succeeds
    config = get_adjustment_v1_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # B. Entity counts are correct
    assert len(gt.merchants) == 1
    assert len(gt.orders) == 2
    assert len(gt.payments) == 2
    assert len(gt.adjustments) == 1
    assert len(gt.settlement_transactions) == 3
    assert len(gt.settlements) == 1
    assert len(gt.bank_entries) == 1

    o1 = gt.orders[0]
    o2 = gt.orders[1]
    p1 = gt.payments[0]
    p2 = gt.payments[1]
    a1 = gt.adjustments[0]
    s1 = gt.settlements[0]
    b1 = gt.bank_entries[0]

    # Invariants 10 & 11: All monetary amounts use Decimal, no floats
    for obj in [o1, o2, p1, p2, a1, s1, b1] + gt.settlement_transactions:
        for field_name, value in obj.model_dump().items():
            if "amount" in field_name or field_name in ("fee", "tax", "fees"):
                assert isinstance(getattr(obj, field_name), Decimal), f"{obj}.{field_name} is not Decimal"
                assert not isinstance(getattr(obj, field_name), float), f"{obj}.{field_name} is float"

    # C. Payment P1 calculation
    assert o1.amount == Decimal("10000.00")
    assert o1.status == OrderStatus.PAID
    assert p1.order_id == o1.order_id
    assert p1.amount == Decimal("10000.00")
    assert p1.fee == Decimal("200.00")
    assert p1.tax == Decimal("36.00")
    assert p1.status == PaymentStatus.CAPTURED
    assert p1.settlement_id == s1.settlement_id

    # D. Payment P2 calculation
    assert o2.amount == Decimal("5000.00")
    assert o2.status == OrderStatus.PAID
    assert p2.order_id == o2.order_id
    assert p2.amount == Decimal("5000.00")
    assert p2.fee == Decimal("100.00")
    assert p2.tax == Decimal("18.00")
    assert p2.status == PaymentStatus.CAPTURED
    assert p2.settlement_id == s1.settlement_id

    # E. Adjustment
    assert a1.amount == Decimal("-250.00")
    assert a1.reason == "chargeback"
    assert a1.settlement_id == s1.settlement_id
    assert a1.merchant_id == gt.merchants[0].merchant_id

    # Fetch STXNs
    p1_stxn = next(stxn for stxn in gt.settlement_transactions if stxn.entity_id == p1.payment_id)
    p2_stxn = next(stxn for stxn in gt.settlement_transactions if stxn.entity_id == p2.payment_id)
    a1_stxn = next(stxn for stxn in gt.settlement_transactions if stxn.entity_id == a1.adjustment_id)

    # Invariant 1: Every SettlementTransaction belongs to exactly one Settlement
    for stxn in gt.settlement_transactions:
        assert stxn.settlement_id == s1.settlement_id

    # Payment STXN properties
    assert p1_stxn.entity_type == SettlementTransactionEntityType.PAYMENT
    assert p1_stxn.type == SettlementTransactionType.CREDIT
    assert p1_stxn.amount == Decimal("10000.00")
    assert p1_stxn.fee == Decimal("200.00")
    assert p1_stxn.tax == Decimal("36.00")
    assert p1_stxn.net_amount == Decimal("9764.00")

    assert p2_stxn.entity_type == SettlementTransactionEntityType.PAYMENT
    assert p2_stxn.type == SettlementTransactionType.CREDIT
    assert p2_stxn.amount == Decimal("5000.00")
    assert p2_stxn.fee == Decimal("100.00")
    assert p2_stxn.tax == Decimal("18.00")
    assert p2_stxn.net_amount == Decimal("4882.00")

    # F. Adjustment SettlementTransaction (Invariants 3, 4, 5)
    assert a1_stxn.entity_type == SettlementTransactionEntityType.ADJUSTMENT
    assert a1_stxn.type == SettlementTransactionType.DEBIT
    assert a1_stxn.amount == Decimal("250.00")
    assert a1_stxn.fee == Decimal("0.00")
    assert a1_stxn.tax == Decimal("0.00")
    assert a1_stxn.net_amount == Decimal("-250.00")

    # Expected settlement transaction composition: 2 credit transactions, 1 debit transaction
    credits = [stxn for stxn in gt.settlement_transactions if stxn.type == SettlementTransactionType.CREDIT]
    debits = [stxn for stxn in gt.settlement_transactions if stxn.type == SettlementTransactionType.DEBIT]
    assert len(credits) == 2
    assert len(debits) == 1

    # G. Settlement equation & H. Settlement amount (Invariant 6)
    expected_setl_amount = p1_stxn.net_amount + p2_stxn.net_amount + a1_stxn.net_amount
    assert expected_setl_amount == Decimal("14396.00")
    assert s1.amount == expected_setl_amount
    assert s1.status == SettlementStatus.PROCESSED
    assert s1.fees == Decimal("300.00")
    assert s1.tax == Decimal("54.00")

    # Invariant 7: Settlement amount is positive
    assert s1.amount > Decimal("0")

    # I. BankEntry amount & J. BankEntry is positive (Invariants 8, 9)
    assert b1.amount == Decimal("14396.00")
    assert b1.amount == s1.amount
    assert b1.amount > Decimal("0")

    # K. Ground Truth contains all expected relationships and metadata
    assert p1_stxn.settlement_id == s1.settlement_id
    assert p2_stxn.settlement_id == s1.settlement_id
    assert a1_stxn.settlement_id == s1.settlement_id
    assert b1.utr == s1.utr
    assert s1.utr is not None and s1.utr.startswith("MOCKUTR")

    # Check Scenario Label & Settlement Equation in Ground Truth
    assert s1.settlement_id in gt.scenario_labels
    assert gt.scenario_labels[s1.settlement_id].scenario_type == "adjustment_v1"

    assert s1.settlement_id in gt.settlement_equations
    eq = gt.settlement_equations[s1.settlement_id]
    assert eq.is_balanced is True
    assert eq.expected_amount == Decimal("14396.00")
    assert eq.sum_of_net_amounts == Decimal("14396.00")
    assert eq.total_fees == Decimal("300.00")
    assert eq.total_tax == Decimal("54.00")

    # Chronological timeline assertions
    assert o1.created_at < p1.created_at < p1.captured_at
    assert p1.captured_at < o2.created_at < p2.created_at < p2.captured_at
    assert p2.captured_at < a1.created_at
    assert a1.created_at < s1.created_at
    assert s1.created_at < b1.transaction_date


def test_determinism_adjustment_v1():
    # L. Repeated generation with the same seed is identical (Invariant 13)
    gt_a1 = Simulator(get_adjustment_v1_config(42)).run()
    gt_a2 = Simulator(get_adjustment_v1_config(42)).run()
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # Different seed produces different output
    gt_b = Simulator(get_adjustment_v1_config(99)).run()
    assert gt_a1.model_dump() != gt_b.model_dump()
