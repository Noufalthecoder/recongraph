"""
Tests for the many-to-one financial lifecycle scenario.
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.common import Currency
from backend.app.models.settlement_transaction import SettlementTransactionType

def get_many_to_one_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=5,
        scenario_type="many_to_one_v1"
    )

def test_many_to_one_lifecycle_generation():
    """Test 5 payments grouping into 1 settlement."""
    config = get_many_to_one_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # 1-2, 5. Counts
    assert len(gt.merchants) == 1
    assert len(gt.orders) == 5
    assert len(gt.payments) == 5
    assert len(gt.settlement_transactions) == 5
    assert len(gt.settlements) == 1
    assert len(gt.bank_entries) == 1

    merchant = gt.merchants[0]
    settlement = gt.settlements[0]
    bank_entry = gt.bank_entries[0]

    # 8. All five SettlementTransactions reference the same Settlement
    assert all(stxn.settlement_id == settlement.settlement_id for stxn in gt.settlement_transactions)
    assert all(payment.settlement_id == settlement.settlement_id for payment in gt.payments)

    expected_total = Decimal("13200.00")
    actual_payment_sum = sum(p.amount for p in gt.payments)
    actual_stxn_sum = sum(stxn.amount for stxn in gt.settlement_transactions)

    # 9. Settlement amount equals the exact Decimal sum of all five payment amounts
    assert settlement.amount == expected_total
    assert settlement.amount == actual_payment_sum
    assert settlement.amount == actual_stxn_sum

    # 10. BankEntry amount equals Settlement amount
    assert bank_entry.amount == settlement.amount

    # 11. Settlement UTR equals BankEntry UTR
    assert settlement.utr == bank_entry.utr

    # Relationship map checks
    for p, o, stxn in zip(gt.payments, gt.orders, gt.settlement_transactions):
        # 3. Every payment belongs to one generated order
        assert p.order_id == o.order_id
        # 4. Every payment belongs to the merchant
        assert p.merchant_id == merchant.merchant_id
        # 6. Every SettlementTransaction represents one payment
        assert stxn.entity_id == p.payment_id
        assert stxn.entity_type == "payment"
        # 7. Every payment appears exactly once in the settlement composition (implicit by counts + 1:1 zip)

    # 12. Ground Truth contains scenario label
    assert gt.scenario_labels[settlement.settlement_id].scenario_type == "many_to_one_v1"

    # 15. No float is used for financial values
    assert isinstance(settlement.amount, Decimal)

def test_determinism_many_to_one():
    """Test same seed produces identical output, different seed produces different."""
    gt_a1 = Simulator(get_many_to_one_config(42)).run()
    gt_a2 = Simulator(get_many_to_one_config(42)).run()
    gt_b = Simulator(get_many_to_one_config(99)).run()

    # 13. Same seed produces identical output
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # 14. Different seed produces different synthetic world
    assert gt_a1.model_dump() != gt_b.model_dump()
    assert gt_a1.merchants[0].merchant_id != gt_b.merchants[0].merchant_id
