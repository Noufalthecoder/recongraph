"""
Tests for InvestigationContext and InvestigationContextBuilder.
"""

from decimal import Decimal
import pytest

from backend.app.investigation.context import (
    InvestigationContext,
    InvestigationContextBuilder,
)


def test_investigation_context_builder_and_rendering():
    """Verify context builder extracts facts and produces structured prompt context."""
    raw_tool_results = [
        {
            "tool_name": "get_settlement_investigation",
            "structured_data": {
                "settlement_id": "setl_101",
                "status": "EXCEPTION",
                "summary_facts": {
                    "settlement_amount": "14396.00",
                    "bank_amount": "14146.00",
                    "difference": "-250.00",
                },
                "exceptions": [{"rule_code": "BANK_AMOUNT_MISMATCH"}],
                "evidence": [
                    {
                        "rule_code": "BANK_AMOUNT_MISMATCH",
                        "difference": Decimal("-250.00"),
                        "expected_value": "14396.00",
                        "observed_value": "14146.00",
                    }
                ],
            },
            "evidence_refs": ["settlement:setl_101", "bank_entry:bank_101"],
        }
    ]

    ctx = InvestigationContextBuilder.build(
        target_entity_type="settlement",
        target_entity_id="setl_101",
        tool_results=raw_tool_results,
    )

    assert ctx.target_entity_id == "setl_101"
    assert ctx.reconciliation_status == "EXCEPTION"
    assert ctx.facts["settlement_amount"] == "14396.00"
    assert ctx.facts["difference"] == "-250.00"
    assert len(ctx.citations) >= 2

    # Render prompt context
    prompt_str = ctx.to_prompt_context()
    assert "<investigation_context>" in prompt_str
    assert "settlement_amount = 14396.00" in prompt_str
    assert "BANK_AMOUNT_MISMATCH" in prompt_str
