"""
High-level service interface for running AI investigations over reconciliation results and graphs.
"""

from typing import Optional

from backend.app.graph import FinancialGraphBuilder
from backend.app.investigation.agent import AIInvestigationAgent
from backend.app.investigation.models import (
    InvestigationAnswer,
    InvestigationRequest,
)
from backend.app.investigation.providers import (
    DeterministicMockProvider,
    LLMProvider,
)
from backend.app.investigation.tools import InvestigationToolRegistry
from backend.app.reconciliation import DeterministicReconciliationEngine
from backend.app.reconciliation.models import ReconciliationResult
from simulator.observed.models import ObservedWorld


class InvestigationService:
    """
    Top-level application facade orchestrating reconciliation, graph construction,
    and the AI investigation agent.
    """

    def __init__(
        self,
        engine: Optional[DeterministicReconciliationEngine] = None,
        provider: Optional[LLMProvider] = None,
    ):
        self.engine = engine or DeterministicReconciliationEngine()
        self.provider = provider or DeterministicMockProvider()

    def investigate(
        self,
        observed_world: ObservedWorld,
        reconciliation_result: Optional[ReconciliationResult] = None,
        question: str = "",
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[str] = None,
    ) -> InvestigationAnswer:
        # Run reconciliation if not already provided
        if reconciliation_result is None:
            reconciliation_result = self.engine.reconcile(observed_world)

        # Build FinancialGraph & Evidence Layer
        graph, evidence_layer = FinancialGraphBuilder.build(
            observed_world, reconciliation_result=reconciliation_result
        )

        # Build Tools & Agent
        tool_registry = InvestigationToolRegistry(
            graph=graph,
            evidence_layer=evidence_layer,
            recon_result=reconciliation_result,
        )
        agent = AIInvestigationAgent(tool_registry=tool_registry, provider=self.provider)

        request = InvestigationRequest(
            question=question,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
        )

        return agent.investigate(request)
