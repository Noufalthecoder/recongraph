"""
Tests for specific operator investigation queries: settlement discrepancy, multi-hop trace, refunds, and many-to-one.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.investigation import InvestigationService
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
)


def test_section_33_adjustment_discrepancy_query():
    """
    Step 10 Section 33 requirement:
    Test settlement discrepancy on adjustment scenario with injected bank delta -₹250.
    Question: 'Why is settlement S1 short by ₹250?'
    """
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=2,
        scenario_type="adjustment_v1",
    )
    gt = Simulator(sim_config).run()

    # Inject bank delta -250.00
    spec = AnomalySpec(
        anomaly_type=AnomalyType.AMOUNT_MISMATCH,
        target_entity_type="bank_entry",
        target_field="amount",
        delta=Decimal("-250.00"),
        target_index=0,
    )
    obs_world, _ = ObservationGenerator.generate(
        gt, ObservationConfig.with_anomalies(seed=42, anomalies=[spec])
    )

    service = InvestigationService()
    setl_id = obs_world.settlements[0].settlement_id

    ans = service.investigate(
        observed_world=obs_world,
        question=f"Why is settlement {setl_id} short by ₹250?",
    )

    assert ans.status.value == "COMPLETED"
    assert setl_id in ans.answer
    assert "BANK_AMOUNT_MISMATCH" in ans.answer
    assert "14,396" in ans.answer or "14396.00" in ans.answer or "14396" in ans.answer
    assert "14,146" in ans.answer or "14146.00" in ans.answer or "14146" in ans.answer
    assert "-250.00" in ans.answer or "-250" in ans.answer


def test_section_34_multihop_payment_trace_query():
    """
    Step 10 Section 34 requirement:
    Test multi-hop trace: 'Trace payment P1 to the bank and tell me whether it reconciles.'
    """
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    service = InvestigationService()
    pay_id = obs_world.payments[0].payment_id

    ans = service.investigate(
        observed_world=obs_world,
        question=f"Trace payment {pay_id} to the bank.",
    )

    assert ans.status.value == "COMPLETED"
    assert pay_id in ans.answer
    assert "RECONCILED" in ans.answer


def test_section_35_refunds_connected_query():
    """
    Step 10 Section 35 requirement:
    Test refunds connection: 'Which refunds are connected to payment P1?'
    """
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=4,
        scenario_type="multiple_refunds_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    service = InvestigationService()
    pay_id = obs_world.payments[0].payment_id

    ans = service.investigate(
        observed_world=obs_world,
        question=f"Which refunds are connected to payment {pay_id}?",
    )

    assert ans.status.value == "COMPLETED"
    assert pay_id in ans.answer


def test_section_36_many_to_one_contributing_payments_query():
    """
    Step 10 Section 36 requirement:
    Test many-to-one contributing payments query.
    """
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=5,
        scenario_type="many_to_one_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    service = InvestigationService()
    setl_id = obs_world.settlements[0].settlement_id

    ans = service.investigate(
        observed_world=obs_world,
        question=f"Which payments contribute to settlement {setl_id}?",
    )

    assert ans.status.value == "COMPLETED"
    assert setl_id in ans.answer
    assert ans.facts.get("payments_count") == 5
