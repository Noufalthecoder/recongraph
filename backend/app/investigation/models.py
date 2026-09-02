"""
Data models for the AI Investigation Layer.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestigationConfidence(str, Enum):
    """Confidence level assigned based on evidence completeness."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvestigationStatus(str, Enum):
    """Outcome status of an investigation request."""
    COMPLETED = "COMPLETED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class InvestigationRequest(BaseModel):
    """Immutable operator question submitted for investigation."""
    model_config = ConfigDict(frozen=True)

    question: str
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[str] = None
    max_tool_calls: int = 5
    max_graph_depth: int = 3


class InvestigationToolCall(BaseModel):
    """Record of a tool invocation made during investigation."""
    model_config = ConfigDict(frozen=True)

    call_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class InvestigationToolResult(BaseModel):
    """Structured output returned by an investigation tool."""
    model_config = ConfigDict(frozen=True)

    tool_name: str
    success: bool
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class InvestigationAnswer(BaseModel):
    """Authoritative, evidence-grounded response produced by the AI Investigator."""
    model_config = ConfigDict(frozen=True)

    answer: str
    status: InvestigationStatus
    confidence: InvestigationConfidence
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[InvestigationToolCall] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)
    suggested_next_steps: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class InvestigationAuditLog(BaseModel):
    """Safe audit trail for operator questions and investigation outcomes."""
    model_config = ConfigDict(frozen=True)

    investigation_id: str
    question: str
    target: Optional[Dict[str, str]] = None
    tools_called: List[str] = Field(default_factory=list)
    status: InvestigationStatus
    confidence: InvestigationConfidence
    timestamp_iso: str
