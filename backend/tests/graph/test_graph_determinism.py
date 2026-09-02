"""
Tests verifying graph determinism, immutability, and GroundTruth import isolation.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder, InvestigationQueryEngine
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_repeated_graph_construction_is_deterministic():
    """Verify building graph twice from same ObservedWorld yields byte-identical output."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=2,
        scenario_type="adjustment_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    graph1, ev1 = FinancialGraphBuilder.build(obs_world)
    graph2, ev2 = FinancialGraphBuilder.build(obs_world)

    assert graph1.model_dump() == graph2.model_dump()


def test_observed_world_not_mutated_during_graph_operations():
    """Verify ObservedWorld is completely unchanged after building and querying graph."""
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

    snapshot_before = obs_world.model_dump()

    graph, evidence = FinancialGraphBuilder.build(obs_world)
    query_engine = InvestigationQueryEngine(graph, evidence)
    _ = query_engine.get_settlement_investigation(obs_world.settlements[0].settlement_id)

    snapshot_after = obs_world.model_dump()
    assert snapshot_before == snapshot_after


def test_no_ground_truth_or_anomaly_leakage_in_graph_package():
    """Verify graph package modules do not import GroundTruth, AnomalyManifest, or random."""
    import backend.app.graph.builder
    import backend.app.graph.evidence
    import backend.app.graph.index
    import backend.app.graph.models
    import backend.app.graph.queries
    import backend.app.graph.traversal

    modules = [
        backend.app.graph.builder,
        backend.app.graph.evidence,
        backend.app.graph.index,
        backend.app.graph.models,
        backend.app.graph.queries,
        backend.app.graph.traversal,
    ]

    for m in modules:
        src = open(m.__file__, "r", encoding="utf-8").read()
        assert "GroundTruth" not in src
        assert "AnomalyManifest" not in src
        assert "AnomalyRecord" not in src
        assert "ScenarioLabel" not in src
        assert "import random" not in src
