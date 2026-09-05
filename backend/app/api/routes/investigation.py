"""
AI Investigation endpoint.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import (
    InvestigationRequestDTO,
    InvestigationResponseDTO,
)
from backend.app.investigation import (
    AIInvestigationAgent,
    InvestigationRequest,
    InvestigationToolRegistry,
)
from backend.app.investigation.providers import get_investigation_provider

router = APIRouter(prefix="/api/investigation", tags=["investigation"])


@router.post("", response_model=InvestigationResponseDTO)
def run_investigation(req: InvestigationRequestDTO, x_scenario_id: Optional[str] = Header(None)):
    bundle = demo_state.get_scenario(x_scenario_id)
    tools = bundle.tools

    provider, provider_mode = get_investigation_provider()
    agent = AIInvestigationAgent(tool_registry=tools, provider=provider)

    inv_req = InvestigationRequest(
        question=req.question,
        target_entity_type=req.target_type,
        target_entity_id=req.target_id,
    )

    ans = agent.investigate(inv_req)

    # Extract finding snippet from answer text
    lines = ans.answer.split("\n")
    finding_lines = []
    in_finding = False
    for line in lines:
        if line.startswith("FINDING"):
            in_finding = True
            continue
        elif any(line.startswith(h) for h in ["EVIDENCE", "FINANCIAL BREAKDOWN", "AFFECTED RECORDS", "RECOMMENDED NEXT CHECK"]):
            in_finding = False
        elif in_finding and line.strip():
            finding_lines.append(line.strip())

    finding_str = " ".join(finding_lines) if finding_lines else ans.answer

    # Extract affected records list
    aff_records = []
    in_aff = False
    for line in lines:
        if line.startswith("AFFECTED RECORDS"):
            in_aff = True
            continue
        elif any(line.startswith(h) for h in ["RECOMMENDED NEXT CHECK", "FINDING", "EVIDENCE", "FINANCIAL BREAKDOWN"]):
            in_aff = False
        elif in_aff and line.strip():
            aff_records.append(line.strip().lstrip("-* "))

    return InvestigationResponseDTO(
        question=req.question,
        status=ans.status.value,
        confidence=ans.confidence.value,
        provider_mode=provider_mode,
        answer=ans.answer,
        finding=finding_str,
        evidence=ans.evidence,
        citations=ans.citations,
        affected_records=aff_records,
        financial_breakdown=ans.facts.get("mathematical_breakdown", ans.facts),
        recommended_next_check=ans.suggested_next_steps,
        suggested_next_steps=ans.suggested_next_steps,
        tool_calls=[tc.model_dump() for tc in ans.tool_calls],
    )
