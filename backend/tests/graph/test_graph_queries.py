"""
Tests for high-level investigation queries on settlements, payments, orders, refunds, and adjustments.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder, InvestigationQueryEngine
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_settlement_investigation_query():
    """Verify get_settlement_investigation produces complete causal neighborhood and breakdown."""
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

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    query_engine = InvestigationQueryEngine(graph, evidence)

    setl_id = obs_world.settlements[0].settlement_id
    res = query_engine.get_settlement_investigation(setl_id)

    assert res.target.entity_id == setl_id
    assert res.target_node is not None
    assert res.reconciliation_status == "RECONCILED"
    assert res.summary_facts["constituent_transactions_count"] == 5
    assert res.summary_facts["payments_count"] == 5
    assert len(res.connected_nodes) == 18

    # Verify mathematical breakdown matches settlement
    breakdown = res.summary_facts["mathematical_breakdown"]
    assert breakdown["composition_delta"] == "0.00"
    assert breakdown["bank_delta"] == "0.00"


def test_payment_and_refund_investigation_queries():
    """Verify get_payment_investigation and get_refund_investigation return linked contexts."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=2,
        scenario_type="refund_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    query_engine = InvestigationQueryEngine(graph, evidence)

    # Payment investigation
    pay_id = obs_world.payments[0].payment_id
    p_res = query_engine.get_payment_investigation(pay_id)
    assert p_res.target_node is not None
    assert p_res.summary_facts["payment_id"] == pay_id

    # Refund investigation
    ref_id = obs_world.refunds[0].refund_id
    r_res = query_engine.get_refund_investigation(ref_id)
    assert r_res.target_node is not None
    assert r_res.summary_facts["refund_id"] == ref_id
    assert r_res.summary_facts["payment_id"] == obs_world.refunds[0].payment_id
