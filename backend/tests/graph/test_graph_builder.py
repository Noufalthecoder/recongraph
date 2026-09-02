"""
Tests for FinancialGraphBuilder constructing graph from ObservedWorld.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_builder_constructs_complete_graph_from_minimal_lifecycle():
    """Verify all 6 entities in minimal lifecycle become nodes and form proper edges."""
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

    graph, evidence = FinancialGraphBuilder.build(obs_world)

    # In minimal lifecycle: 1 merchant, 1 order, 1 payment, 1 stxn, 1 settlement, 1 bank entry = 6 nodes
    assert graph.node_count == 6

    node_types = {n.entity_type for n in graph.nodes}
    assert node_types == {"merchant", "order", "payment", "settlement_transaction", "settlement", "bank_entry"}

    # Edges: merchant->order, order->payment, payment->stxn, stxn->settlement, settlement->bank_entry = 5 edges
    assert graph.edge_count == 5
    rel_types = {e.relationship_type for e in graph.edges}
    assert rel_types == {"OWNS_ORDER", "HAS_PAYMENT", "SETTLED_AS", "BELONGS_TO_SETTLEMENT", "SETTLED_TO_BANK"}


def test_builder_attaches_reconciliation_result_evidence():
    """Verify evidence is attached to nodes when ReconciliationResult is supplied."""
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

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)

    setl_node_id = f"settlement:{obs_world.settlements[0].settlement_id}"
    assert evidence.get_node_status(setl_node_id) == "RECONCILED"

    node_ev = evidence.get_node_evidence(setl_node_id)
    assert len(node_ev) > 0
    assert node_ev[0].status == "RECONCILED"
