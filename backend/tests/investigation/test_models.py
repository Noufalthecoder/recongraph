"""
Tests for investigation data models: InvestigationRequest, InvestigationAnswer, ToolCalls, Status, and Confidence.
"""

import pytest
from pydantic import ValidationError

from backend.app.investigation.models import (
    InvestigationAnswer,
    InvestigationConfidence,
    InvestigationRequest,
    InvestigationStatus,
    InvestigationToolCall,
    InvestigationToolResult,
)


def test_investigation_request_immutability():
    """Verify InvestigationRequest is frozen and stores query configuration."""
    req = InvestigationRequest(
        question="Why is settlement setl_001 short by ₹250?",
        target_entity_type="settlement",
        target_entity_id="setl_001",
        max_tool_calls=5,
    )
    assert req.question == "Why is settlement setl_001 short by ₹250?"
    assert req.target_entity_id == "setl_001"

    with pytest.raises(ValidationError):
        req.question = "Modified"


def test_investigation_answer_model():
    """Verify InvestigationAnswer stores structured facts, citations, and confidence."""
    ans = InvestigationAnswer(
        answer="Settlement setl_001 has a bank mismatch of ₹250.",
        status=InvestigationStatus.COMPLETED,
        confidence=InvestigationConfidence.HIGH,
        evidence=[{"rule_code": "BANK_AMOUNT_MISMATCH"}],
        facts={"settlement_id": "setl_001", "difference": "-250.00"},
        suggested_next_steps=["Check bank statement transaction."],
        citations=["[E1] Settlement setl_001", "[E2] BANK_AMOUNT_MISMATCH"],
    )

    assert ans.status == InvestigationStatus.COMPLETED
    assert ans.confidence == InvestigationConfidence.HIGH
    assert len(ans.citations) == 2
    assert ans.facts["difference"] == "-250.00"
