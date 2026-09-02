"""
AI Investigation Agent Package for ReconGraph.
"""

from backend.app.investigation.agent import AIInvestigationAgent
from backend.app.investigation.context import (
    InvestigationContext,
    InvestigationContextBuilder,
)
from backend.app.investigation.guardrails import (
    AnswerValidator,
    DataExfiltrationGuard,
    PromptInjectionGuard,
)
from backend.app.investigation.models import (
    InvestigationAnswer,
    InvestigationConfidence,
    InvestigationRequest,
    InvestigationStatus,
    InvestigationToolCall,
    InvestigationToolResult,
)
from backend.app.investigation.prompts import (
    INVESTIGATION_SYSTEM_PROMPT,
    build_investigation_user_prompt,
)
from backend.app.investigation.providers import (
    DeterministicMockProvider,
    LLMProvider,
    OpenAICompatibleProvider,
)
from backend.app.investigation.service import InvestigationService
from backend.app.investigation.tools import InvestigationToolRegistry

__all__ = [
    "AIInvestigationAgent",
    "InvestigationService",
    "InvestigationRequest",
    "InvestigationAnswer",
    "InvestigationStatus",
    "InvestigationConfidence",
    "InvestigationToolCall",
    "InvestigationToolResult",
    "InvestigationToolRegistry",
    "InvestigationContext",
    "InvestigationContextBuilder",
    "PromptInjectionGuard",
    "DataExfiltrationGuard",
    "AnswerValidator",
    "LLMProvider",
    "DeterministicMockProvider",
    "OpenAICompatibleProvider",
    "INVESTIGATION_SYSTEM_PROMPT",
    "build_investigation_user_prompt",
]
