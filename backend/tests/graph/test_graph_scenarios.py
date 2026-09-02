"""
Tests for graph construction across all 6 clean and anomaly scenarios.
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


@pytest.mark.parametrize(
    "scenario_name,expected_node_count",
    [
        ("minimal_lifecycle_v1", 6),
        ("many_to_one_v1", 18),
        ("many_to_one_with_fee_tax_v1", 18),
        ("refund_v1", 13),
        ("multiple_refunds_v1", 27),
        ("adjustment_v1", 11),
    ],
)
def test_all_six_clean_scenarios_graph_construction(scenario_name: str, expected_node_count: int):
    """Verify graph builds with exact expected node count across all 6 clean scenarios."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type=scenario_name,
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)

    assert graph.node_count == expected_node_count
    assert graph.edge_count > 0

    # Verify query engine runs on every settlement
    query_engine = InvestigationQueryEngine(graph, evidence)
    for s in obs_world.settlements:
        inv = query_engine.get_settlement_investigation(s.settlement_id)
        assert inv.reconciliation_status == "RECONCILED"
        assert len(inv.connected_nodes) > 0


def test_missing_record_anomaly_in_graph():
    """Verify missing record is faithfully absent from graph without being hallucinated."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()

    # Drop STXN
    spec = AnomalySpec(
        anomaly_type=AnomalyType.MISSING_RECORD,
        target_entity_type="settlement_transaction",
        target_index=0,
    )
    obs_world, manifest = ObservationGenerator.generate(
        gt, ObservationConfig.with_anomalies(seed=42, anomalies=[spec])
    )

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)

    # In minimal lifecycle without STXN: 5 nodes (merchant, order, payment, settlement, bank_entry)
    assert graph.node_count == 5
    assert not any(n.entity_type == "settlement_transaction" for n in graph.nodes)

    query_engine = InvestigationQueryEngine(graph, evidence)
    setl_inv = query_engine.get_settlement_investigation(obs_world.settlements[0].settlement_id)
    assert setl_inv.reconciliation_status == "EXCEPTION"


def test_identifier_mismatch_anomaly_in_graph():
    """Verify corrupted UTR in BankEntry is faithfully represented in graph attributes."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()

    spec = AnomalySpec(
        anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
        target_entity_type="bank_entry",
        target_field="utr",
        target_index=0,
    )
    obs_world, _ = ObservationGenerator.generate(
        gt, ObservationConfig.with_anomalies(seed=42, anomalies=[spec])
    )

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)

    b_node = next(n for n in graph.nodes if n.entity_type == "bank_entry")
    assert b_node.attributes["utr"].endswith("_MISMATCH")

    query_engine = InvestigationQueryEngine(graph, evidence)
    setl_inv = query_engine.get_settlement_investigation(obs_world.settlements[0].settlement_id)
    assert setl_inv.reconciliation_status == "EXCEPTION"


def test_duplicate_record_anomaly_in_graph():
    """Verify duplicate record injected into ObservedWorld results in proper node representation."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()

    spec = AnomalySpec(
        anomaly_type=AnomalyType.DUPLICATE_RECORD,
        target_entity_type="payment",
        target_index=0,
    )
    obs_world, _ = ObservationGenerator.generate(
        gt, ObservationConfig.with_anomalies(seed=42, anomalies=[spec])
    )

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)

    query_engine = InvestigationQueryEngine(graph, evidence)
    first_exc = recon_res.exceptions[0]
    inv_res = query_engine.get_exception_neighborhood(first_exc)
    assert inv_res.reconciliation_status == "EXCEPTION"


def test_large_batch_graph_performance():
    """Verify graph builds and executes investigations on 100+ record datasets with high performance."""
    import time
    from backend.app.benchmark import BenchmarkRunner

    runner = BenchmarkRunner()
    gt = runner._generate_large_batch_ground_truth(target_records=100, seed=42)
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    t0 = time.perf_counter()
    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    query_engine = InvestigationQueryEngine(graph, evidence)

    # Run investigations across all settlements
    for s in obs_world.settlements:
        inv = query_engine.get_settlement_investigation(s.settlement_id)
        assert inv.reconciliation_status == "RECONCILED"

    elapsed = time.perf_counter() - t0
    assert graph.node_count >= 50
    assert elapsed < 1.0  # Fast sub-second execution

