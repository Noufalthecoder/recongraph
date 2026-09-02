"""
Tests for read-only InvestigationToolRegistry and tool query outputs.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder
from backend.app.investigation import InvestigationToolRegistry
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


@pytest.fixture
def setup_tools():
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

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    tools = InvestigationToolRegistry(graph, evidence, recon_result=recon_res)

    return obs_world, tools


def test_search_financial_entities(setup_tools):
    obs_world, tools = setup_tools
    setl_id = obs_world.settlements[0].settlement_id

    res = tools.search_financial_entities(setl_id)
    assert res.success is True
    assert res.structured_data["candidates_count"] >= 1
    assert any(c["entity_id"] == setl_id for c in res.structured_data["candidates"])


def test_get_settlement_investigation_tool(setup_tools):
    obs_world, tools = setup_tools
    setl_id = obs_world.settlements[0].settlement_id

    res = tools.get_settlement_investigation(setl_id)
    assert res.success is True
    assert res.structured_data["settlement_id"] == setl_id
    assert "mathematical_breakdown" in res.structured_data["summary_facts"]


def test_get_payment_and_adjustment_investigation_tools(setup_tools):
    obs_world, tools = setup_tools
    pay_id = obs_world.payments[0].payment_id
    adj_id = obs_world.adjustments[0].adjustment_id

    p_res = tools.get_payment_investigation(pay_id)
    assert p_res.success is True
    assert p_res.structured_data["payment_id"] == pay_id

    a_res = tools.get_adjustment_investigation(adj_id)
    assert a_res.success is True
    assert a_res.structured_data["adjustment_id"] == adj_id


def test_get_graph_path_and_neighbors(setup_tools):
    obs_world, tools = setup_tools
    src = f"merchant:{obs_world.merchants[0].merchant_id}"
    dst = f"bank_entry:{obs_world.bank_entries[0].bank_entry_id}"

    path_res = tools.get_graph_path(src, dst)
    assert path_res.success is True
    assert len(path_res.structured_data["path"]) >= 4

    neigh_res = tools.get_graph_neighbors(src, direction="outgoing")
    assert neigh_res.success is True
    assert neigh_res.structured_data["neighbors_count"] >= 1
