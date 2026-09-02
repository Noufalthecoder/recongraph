"""
Tests for graph traversal algorithms: neighbors, ancestors, descendants, subgraph, and path finding.
"""

from datetime import date
import pytest

from backend.app.graph import (
    FinancialGraphBuilder,
    GraphIndex,
    find_path,
    get_ancestors,
    get_descendants,
    get_neighbors,
    get_subgraph,
)
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_ancestors_and_descendants_traversal():
    """Verify ancestors and descendants traverse the full financial lifecycle backwards and forwards."""
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

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    merch_node_id = f"merchant:{obs_world.merchants[0].merchant_id}"
    bank_node_id = f"bank_entry:{obs_world.bank_entries[0].bank_entry_id}"
    setl_node_id = f"settlement:{obs_world.settlements[0].settlement_id}"

    # Descendants of Merchant should include Order, Payment, STXN, Settlement, BankEntry (5 nodes)
    desc = get_descendants(index, merch_node_id)
    assert len(desc) == 5
    assert any(n.node_id == bank_node_id for n in desc)

    # Ancestors of BankEntry should include Settlement, STXN, Payment, Order, Merchant (5 nodes)
    anc = get_ancestors(index, bank_node_id)
    assert len(anc) == 5
    assert any(n.node_id == merch_node_id for n in anc)


def test_subgraph_extraction():
    """Verify get_subgraph returns the correct bounded neighborhood and edges."""
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

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    pay_node_id = f"payment:{obs_world.payments[0].payment_id}"

    # Depth 1 from Payment should include Order and STXN + Payment itself = 3 nodes
    sub_nodes, sub_edges = get_subgraph(index, pay_node_id, max_depth=1)
    assert len(sub_nodes) == 3
    assert any(n.entity_type == "order" for n in sub_nodes)
    assert any(n.entity_type == "settlement_transaction" for n in sub_nodes)
    assert len(sub_edges) == 2


def test_path_finding_from_merchant_to_bank_entry():
    """Verify find_path finds the deterministic causal route from Merchant to BankEntry."""
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

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    src = f"merchant:{obs_world.merchants[0].merchant_id}"
    dst = f"bank_entry:{obs_world.bank_entries[0].bank_entry_id}"

    path = find_path(index, src, dst)
    assert path is not None
    assert len(path) == 6
    assert path[0].startswith("merchant:")
    assert path[1].startswith("order:")
    assert path[2].startswith("payment:")
    assert path[3].startswith("settlement_transaction:")
    assert path[4].startswith("settlement:")
    assert path[5].startswith("bank_entry:")
