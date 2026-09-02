"""
Tests for graph evidence integration and exception neighborhood investigations.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder, InvestigationQueryEngine
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
)


def test_exception_neighborhood_investigation_on_amount_mismatch():
    """Verify exception neighborhood retrieves mutated entity, causal nodes, and exact discrepancy."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()

    # Inject bank amount mismatch (-250.00)
    spec = AnomalySpec(
        anomaly_type=AnomalyType.AMOUNT_MISMATCH,
        target_entity_type="bank_entry",
        target_field="amount",
        delta=Decimal("-250.00"),
        target_index=0,
    )
    obs_world, manifest = ObservationGenerator.generate(
        gt, ObservationConfig.with_anomalies(seed=42, anomalies=[spec])
    )

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    assert len(recon_res.exceptions) > 0

    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    query_engine = InvestigationQueryEngine(graph, evidence)

    # Investigate the exception
    first_exc = recon_res.exceptions[0]
    inv_res = query_engine.get_exception_neighborhood(first_exc)

    assert inv_res.reconciliation_status == "EXCEPTION"
    assert len(inv_res.exceptions) > 0
    assert inv_res.summary_facts["exception_rule"] == first_exc.rule_code

    # Investigate the settlement directly
    setl_id = obs_world.settlements[0].settlement_id
    setl_inv = query_engine.get_settlement_investigation(setl_id)
    assert setl_inv.reconciliation_status == "EXCEPTION"
    breakdown = setl_inv.summary_facts["mathematical_breakdown"]
    assert breakdown["bank_delta"] == "-250.00"
