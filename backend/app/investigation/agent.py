"""
AI Investigation Agent orchestrating tools, context building, guardrails, and grounded response synthesis.
"""

import re
from typing import Any, Dict, List, Optional

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
)
from backend.app.investigation.prompts import (
    INVESTIGATION_SYSTEM_PROMPT,
    build_investigation_user_prompt,
)
from backend.app.investigation.providers import (
    DeterministicMockProvider,
    LLMProvider,
)
from backend.app.investigation.tools import InvestigationToolRegistry


class AIInvestigationAgent:
    """
    Operator-facing AI Investigation Agent providing evidence-grounded explanations
    of reconciliation exceptions and financial lifecycles.
    """

    def __init__(
        self,
        tool_registry: InvestigationToolRegistry,
        provider: Optional[LLMProvider] = None,
    ):
        self.tools = tool_registry
        self.provider = provider or DeterministicMockProvider()

    def investigate(self, request: InvestigationRequest) -> InvestigationAnswer:
        tool_calls: List[InvestigationToolCall] = []

        # ---------------------------------------------------------------------
        # 1. Security Guardrails Check
        # ---------------------------------------------------------------------
        ok_inj, msg_inj = PromptInjectionGuard.check(request.question)
        if not ok_inj:
            return InvestigationAnswer(
                answer=msg_inj or "Query rejected by security policies.",
                status=InvestigationStatus.SECURITY_VIOLATION,
                confidence=InvestigationConfidence.LOW,
                tool_calls=[],
                suggested_next_steps=["Rephrase query to adhere to financial security policies."],
            )

        ok_exf, msg_exf = DataExfiltrationGuard.check(request.question)
        if not ok_exf:
            return InvestigationAnswer(
                answer=msg_exf or "Query rejected by data protection policies.",
                status=InvestigationStatus.SECURITY_VIOLATION,
                confidence=InvestigationConfidence.LOW,
                tool_calls=[],
                suggested_next_steps=["Query must target observable financial records."],
            )

        # ---------------------------------------------------------------------
        # 2. Unsupported Questions Check (e.g. fraud, external topics)
        # ---------------------------------------------------------------------
        unsupported_terms = ["fraud", "fraudulent", "credit score", "weather", "stock price", "crypto"]
        if any(term in request.question.lower() for term in unsupported_terms):
            return InvestigationAnswer(
                answer="I do not have evidence or domain capability in the reconciliation dataset to evaluate this topic. Please ask questions about observed settlements, transactions, amounts, or exceptions.",
                status=InvestigationStatus.UNSUPPORTED_QUERY,
                confidence=InvestigationConfidence.LOW,
                tool_calls=[],
                suggested_next_steps=["Inspect bank statements or dispute portals directly."],
            )

        # ---------------------------------------------------------------------
        # 3. Entity Target Resolution
        # ---------------------------------------------------------------------
        target_type = request.target_entity_type
        target_id = request.target_entity_id

        if not target_id:
            # Try to identify entity from question text
            # Look for regex patterns e.g. setl_..., pay_..., ord_..., ref_..., adj_..., bank_...
            match = re.search(r"\b(setl_[a-zA-Z0-9_]+|pay_[a-zA-Z0-9_]+|ord_[a-zA-Z0-9_]+|ref_[a-zA-Z0-9_]+|adj_[a-zA-Z0-9_]+|bank_[a-zA-Z0-9_]+)\b", request.question)
            if match:
                target_id = match.group(1)
                prefix = target_id.split("_")[0]
                prefix_map = {
                    "setl": "settlement",
                    "pay": "payment",
                    "ord": "order",
                    "ref": "refund",
                    "adj": "adjustment",
                    "bank": "bank_entry",
                }
                target_type = prefix_map.get(prefix, target_type)

        if not target_id:
            # Fallback to search
            search_res = self.tools.search_financial_entities(request.question)
            tool_calls.append(
                InvestigationToolCall(
                    call_id="call_001",
                    tool_name="search_financial_entities",
                    arguments={"query": request.question},
                )
            )
            candidates = search_res.structured_data.get("candidates", [])

            if len(candidates) > 1:
                labels = ", ".join(c["display_label"] for c in candidates[:5])
                return InvestigationAnswer(
                    answer=f"I found multiple candidate records matching your query ({labels}). Please specify the exact settlement ID or entity ID to investigate.",
                    status=InvestigationStatus.NEEDS_CLARIFICATION,
                    confidence=InvestigationConfidence.LOW,
                    tool_calls=tool_calls,
                    facts={"candidates_count": len(candidates)},
                    suggested_next_steps=["Provide explicit settlement or payment ID."],
                )
            elif len(candidates) == 1:
                target_type = candidates[0]["entity_type"]
                target_id = candidates[0]["entity_id"]
            else:
                # If there are settlements in the graph and the question mentions "settlement" or "exception"
                settlements = [n for n in self.tools.graph.nodes if n.entity_type == "settlement"]
                if len(settlements) == 1:
                    target_type = "settlement"
                    target_id = settlements[0].entity_id
                elif len(settlements) > 1:
                    labels = ", ".join(s.entity_id for s in settlements)
                    return InvestigationAnswer(
                        answer=f"Multiple settlements exist in the observed dataset ({labels}). Please specify which settlement ID you wish to investigate.",
                        status=InvestigationStatus.NEEDS_CLARIFICATION,
                        confidence=InvestigationConfidence.LOW,
                        tool_calls=tool_calls,
                        facts={"settlements_count": len(settlements)},
                        suggested_next_steps=["Specify settlement ID (e.g. setl_001)."],
                    )
                else:
                    return InvestigationAnswer(
                        answer="No matching financial record was found in the observed world to answer your question.",
                        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
                        confidence=InvestigationConfidence.LOW,
                        tool_calls=tool_calls,
                        suggested_next_steps=["Check the entity ID spelling."],
                    )

        # ---------------------------------------------------------------------
        # 4. Tool Execution
        # ---------------------------------------------------------------------
        raw_tool_results: List[Dict[str, Any]] = []

        if target_type == "settlement" or (target_id and target_id.startswith("setl_")):
            tool_res = self.tools.get_settlement_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_settlement_investigation",
                    arguments={"settlement_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())
        elif target_type == "payment" or (target_id and target_id.startswith("pay_")):
            tool_res = self.tools.get_payment_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_payment_investigation",
                    arguments={"payment_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())
        elif target_type == "refund" or (target_id and target_id.startswith("ref_")):
            tool_res = self.tools.get_refund_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_refund_investigation",
                    arguments={"refund_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())
        elif target_type == "adjustment" or (target_id and target_id.startswith("adj_")):
            tool_res = self.tools.get_adjustment_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_adjustment_investigation",
                    arguments={"adjustment_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())
        elif target_type == "order" or (target_id and target_id.startswith("ord_")):
            tool_res = self.tools.get_order_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_order_investigation",
                    arguments={"order_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())
        elif target_type == "bank_entry" or (target_id and target_id.startswith("bank_")):
            tool_res = self.tools.get_bank_entry_investigation(target_id)
            tool_calls.append(
                InvestigationToolCall(
                    call_id=f"call_{len(tool_calls)+1:03d}",
                    tool_name="get_bank_entry_investigation",
                    arguments={"bank_entry_id": target_id},
                )
            )
            raw_tool_results.append(tool_res.model_dump())

        # ---------------------------------------------------------------------
        # 5. Build Investigation Context
        # ---------------------------------------------------------------------
        context = InvestigationContextBuilder.build(
            target_entity_type=target_type,
            target_entity_id=target_id,
            tool_results=raw_tool_results,
        )

        # ---------------------------------------------------------------------
        # 6. LLM Generation
        # ---------------------------------------------------------------------
        user_prompt = build_investigation_user_prompt(request.question, context.to_prompt_context())
        raw_answer = self.provider.generate(
            system_prompt=INVESTIGATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context=context,
        )

        # ---------------------------------------------------------------------
        # 7. Answer Validation
        # ---------------------------------------------------------------------
        is_valid, val_err = AnswerValidator.validate(raw_answer, context)
        if not is_valid:
            # Fallback to deterministic safe answer if LLM hallucinated
            safe_fallback = (
                f"FINDING:\nInvestigation for {target_type} {target_id} encountered validation constraints.\n\n"
                f"EVIDENCE:\n" + "\n".join(f"- {c}" for c in context.citations) + "\n\n"
                f"FINANCIAL BREAKDOWN:\n" + "\n".join(f"{k}: {v}" for k, v in context.facts.items() if not isinstance(v, dict)) + "\n\n"
                f"RECOMMENDED NEXT CHECK:\nReview raw evidence for {target_id}."
            )
            return InvestigationAnswer(
                answer=safe_fallback,
                status=InvestigationStatus.VALIDATION_FAILED,
                confidence=InvestigationConfidence.LOW,
                evidence=context.evidence,
                tool_calls=tool_calls,
                facts=context.facts,
                suggested_next_steps=["Review deterministic evidence citations."],
                citations=context.citations,
            )

        confidence = InvestigationConfidence.HIGH if context.citations else InvestigationConfidence.MEDIUM

        suggested = [
            f"Verify bank statement for UTR {context.facts.get('utr', 'N/A')}"
            if "utr" in context.facts
            else f"Inspect constituent transactions for {target_id}"
        ]

        return InvestigationAnswer(
            answer=raw_answer,
            status=InvestigationStatus.COMPLETED,
            confidence=confidence,
            evidence=context.evidence,
            tool_calls=tool_calls,
            facts=context.facts,
            suggested_next_steps=suggested,
            citations=context.citations,
        )
