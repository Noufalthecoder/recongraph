"""
Tests for AIInvestigationAgent execution and responses.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder
from backend.app.investigation import (
    AIInvestigationAgent,
    DeterministicMockProvider,
    InvestigationConfidence,
    InvestigationRequest,
    InvestigationStatus,
    InvestigationToolRegistry,
)
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
)


def test_agent_investigates_settlement_bank_mismatch():
    """Verify agent retrieves settlement investigation and returns grounded answer."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
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

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    tools = InvestigationToolRegistry(graph, evidence, recon_result=recon_res)
    agent = AIInvestigationAgent(tool_registry=tools, provider=DeterministicMockProvider())

    setl_id = obs_world.settlements[0].settlement_id
    req = InvestigationRequest(question=f"Why is settlement {setl_id} short by ₹250?")
    ans = agent.investigate(req)

    assert ans.status == InvestigationStatus.COMPLETED
    assert ans.confidence == InvestigationConfidence.HIGH
    assert setl_id in ans.answer
    assert "-250.00" in ans.answer or "-250" in ans.answer
    assert len(ans.tool_calls) > 0
    assert ans.tool_calls[0].tool_name == "get_settlement_investigation"
    assert len(ans.suggested_next_steps) > 0
