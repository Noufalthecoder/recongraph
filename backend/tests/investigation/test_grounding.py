"""
Tests for evidence grounding, ambiguity handling, missing evidence, and hallucination defense.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder
from backend.app.investigation import (
    AIInvestigationAgent,
    DeterministicMockProvider,
    InvestigationRequest,
    InvestigationStatus,
    InvestigationToolRegistry,
)
from backend.app.reconciliation import DeterministicReconciliationEngine
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


@pytest.fixture
def multi_settlement_agent():
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

    recon_res = DeterministicReconciliationEngine().reconcile(obs_world)
    graph, evidence = FinancialGraphBuilder.build(obs_world, reconciliation_result=recon_res)
    tools = InvestigationToolRegistry(graph, evidence, recon_result=recon_res)
    agent = AIInvestigationAgent(tool_registry=tools, provider=DeterministicMockProvider())
    return agent


def test_ambiguous_question_returns_needs_clarification(multi_settlement_agent):
    """Verify that asking a vague question with multiple settlements prompts for clarification."""
    agent = multi_settlement_agent
    req = InvestigationRequest(question="Why is the settlement not reconciling?")
    ans = agent.investigate(req)

    assert ans.status == InvestigationStatus.NEEDS_CLARIFICATION
    assert "Multiple settlements exist" in ans.answer or "multiple candidate records" in ans.answer


def test_unsupported_fraud_question(multi_settlement_agent):
    """Verify that asking unsupported questions like fraud prediction returns UNSUPPORTED_QUERY."""
    agent = multi_settlement_agent
    req = InvestigationRequest(question="Was this payment a fraudulent transaction?")
    ans = agent.investigate(req)

    assert ans.status == InvestigationStatus.UNSUPPORTED_QUERY
    assert "do not have evidence" in ans.answer


def test_hallucination_attempt_is_intercepted():
    """Verify that if an LLM hallucinates an amount not in context, validator triggers safe fallback."""
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
    tools = InvestigationToolRegistry(graph, evidence, recon_result=recon_res)

    # Provider configured to return a hallucinated amount
    hallucinating_provider = DeterministicMockProvider(
        override_response="FINDING:\nSettlement setl_001 has a shortfall of ₹987,654.00.\n\nEVIDENCE:\nNone\n\nFINANCIAL BREAKDOWN:\nAmount: ₹987,654.00\n\nAFFECTED RECORDS:\n- setl_001\n\nRECOMMENDED NEXT CHECK:\nNone"
    )
    agent = AIInvestigationAgent(tool_registry=tools, provider=hallucinating_provider)

    setl_id = obs_world.settlements[0].settlement_id
    req = InvestigationRequest(question=f"Why is settlement {setl_id} wrong?")
    ans = agent.investigate(req)

    assert ans.status == InvestigationStatus.VALIDATION_FAILED
    assert "validation constraints" in ans.answer.lower()
