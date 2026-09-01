"""
Tests for the many-to-one financial lifecycle scenario with fee and tax.
"""

from datetime import date
from decimal import Decimal
import pytest
import decimal

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.common import Currency
from backend.app.models.settlement_transaction import SettlementTransactionType

def get_fee_tax_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=5,
        scenario_type="many_to_one_with_fee_tax_v1",
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP"
    )

def test_fee_tax_lifecycle_generation():
    """Test 5 payments grouping into 1 settlement with fees and tax."""
    config = get_fee_tax_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # 1. Every payment transaction contains expected fee
    # 2. Every payment transaction contains expected tax
    # 3. net_amount = amount - fee - tax
    # 4-6. Sums are correct
    
    expected_gross = sum(Decimal(amt) for amt in ["1250.00", "3400.00", "850.00", "2100.00", "5600.00"])
    actual_gross = Decimal("0.00")
    actual_fee = Decimal("0.00")
    actual_tax = Decimal("0.00")
    actual_net = Decimal("0.00")
    
    rounding = decimal.ROUND_HALF_UP
    
    for stxn in gt.settlement_transactions:
        # Calculate manually to compare
        expected_fee = (stxn.amount * Decimal("0.02")).quantize(Decimal("0.01"), rounding=rounding)
        expected_tax = (expected_fee * Decimal("0.18")).quantize(Decimal("0.01"), rounding=rounding)
        expected_net = stxn.amount - expected_fee - expected_tax
        
        # Verify 1, 2, 3
        assert stxn.fee == expected_fee
        assert stxn.tax == expected_tax
        assert stxn.net_amount == expected_net
        
        actual_gross += stxn.amount
        actual_fee += stxn.fee
        actual_tax += stxn.tax
        actual_net += stxn.net_amount
        
        # 11. All financial values remain Decimal
        assert isinstance(stxn.amount, Decimal)
        assert isinstance(stxn.fee, Decimal)
        assert isinstance(stxn.tax, Decimal)
        assert isinstance(stxn.net_amount, Decimal)

    # 4. Sum of gross payment amounts is correct
    assert actual_gross == expected_gross
    
    # 5, 6, 7. Sums match settlement
    settlement = gt.settlements[0]
    assert settlement.amount == actual_net
    assert settlement.fees == actual_fee
    assert settlement.tax == actual_tax
    
    # 8. BankEntry.amount equals Settlement.amount
    bank_entry = gt.bank_entries[0]
    assert bank_entry.amount == settlement.amount

    # 13. Ground truth contains every component
    eq = gt.settlement_equations[settlement.settlement_id]
    assert eq.sum_of_net_amounts == actual_net
    assert eq.total_fees == actual_fee
    assert eq.total_tax == actual_tax
    assert eq.is_balanced is True

def test_determinism_fee_tax():
    """Test same seed produces identical output, different seed produces different."""
    gt_a1 = Simulator(get_fee_tax_config(42)).run()
    gt_a2 = Simulator(get_fee_tax_config(42)).run()
    gt_b = Simulator(get_fee_tax_config(99)).run()

    # 14. Same seed produces identical output
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # Different seed produces different synthetic world
    assert gt_a1.model_dump() != gt_b.model_dump()
