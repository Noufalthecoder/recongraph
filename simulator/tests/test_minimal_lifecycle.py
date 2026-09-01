"""
Tests for the minimal financial lifecycle simulator.
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from backend.app.models.common import Currency
from backend.app.models.settlement_transaction import SettlementTransactionType

def get_base_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1
    )

def test_minimal_lifecycle_generation():
    """Test one complete lifecycle can be generated."""
    config = get_base_config(42)
    sim = Simulator(config)
    gt = sim.run()

    # 1. One complete lifecycle generated
    assert len(gt.merchants) == 1
    assert len(gt.orders) == 1
    assert len(gt.payments) == 1
    assert len(gt.settlement_transactions) == 1
    assert len(gt.settlements) == 1
    assert len(gt.bank_entries) == 1

    merchant = gt.merchants[0]
    order = gt.orders[0]
    payment = gt.payments[0]
    stxn = gt.settlement_transactions[0]
    settlement = gt.settlements[0]
    bank_entry = gt.bank_entries[0]

    # 2. Payment belongs to the generated Order
    assert payment.order_id == order.order_id
    
    # 3. Order belongs to the generated Merchant
    assert order.merchant_id == merchant.merchant_id
    assert payment.merchant_id == merchant.merchant_id
    assert settlement.merchant_id == merchant.merchant_id
    assert bank_entry.merchant_id == merchant.merchant_id

    # 4. SettlementTransaction references the correct source payment
    assert stxn.entity_id == payment.payment_id
    assert stxn.entity_type == "payment"
    assert stxn.type == SettlementTransactionType.CREDIT

    # 5. Settlement contains the correct transaction
    assert stxn.settlement_id == settlement.settlement_id
    assert payment.settlement_id == settlement.settlement_id

    # 6. Settlement amount equals payment amount
    assert settlement.amount == payment.amount
    assert settlement.amount == Decimal("1000.00")
    
    # 7. BankEntry amount equals settlement amount
    assert bank_entry.amount == settlement.amount

    # 8. UTR connects the synthetic settlement to the bank entry
    assert bank_entry.utr == settlement.utr
    assert bank_entry.utr.startswith("MOCKUTR")

    # 9. All monetary values remain Decimal
    assert isinstance(order.amount, Decimal)
    assert isinstance(payment.amount, Decimal)
    assert isinstance(payment.fee, Decimal)
    assert isinstance(payment.tax, Decimal)
    assert isinstance(stxn.amount, Decimal)
    assert isinstance(stxn.net_amount, Decimal)
    assert isinstance(settlement.amount, Decimal)
    assert isinstance(bank_entry.amount, Decimal)

    # 10. Ground Truth contains all required IDs and structures
    assert len(gt.scenario_labels) == 1
    assert settlement.settlement_id in gt.scenario_labels
    assert gt.scenario_labels[settlement.settlement_id].scenario_type == "minimal_lifecycle_v1"
    
    # 11. Ground Truth relationships match the generated entities
    # (Implicitly verified by assertions 2-8 above)

def test_determinism():
    """Test same seed produces identical output, different seed produces different."""
    config_a1 = get_base_config(42)
    config_a2 = get_base_config(42)
    config_b = get_base_config(99)

    gt_a1 = Simulator(config_a1).run()
    gt_a2 = Simulator(config_a2).run()
    gt_b = Simulator(config_b).run()

    # 12. Same seed + same configuration produces identical output
    assert gt_a1.model_dump() == gt_a2.model_dump()

    # 13. Different seed produces a different synthetic world
    assert gt_a1.model_dump() != gt_b.model_dump()
    
    # Verify different IDs were generated
    assert gt_a1.merchants[0].merchant_id != gt_b.merchants[0].merchant_id
    assert gt_a1.payments[0].payment_id != gt_b.payments[0].payment_id
