"""
Provider abstraction and deterministic mock / live implementations for the AI Investigator.
"""

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional, Protocol

from backend.app.investigation.context import InvestigationContext


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[InvestigationContext] = None,
    ) -> str:
        ...


class DeterministicMockProvider:
    """
    100% offline, deterministic provider that synthesizes grounded investigation answers
    directly from the retrieved InvestigationContext and rules.
    """

    def __init__(self, override_response: Optional[str] = None):
        self.override_response = override_response

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[InvestigationContext] = None,
    ) -> str:
        if self.override_response is not None:
            return self.override_response

        if context is None:
            return (
                "FINDING\nNo evidence context was provided for investigation.\n\n"
                "EVIDENCE\nNone\n\n"
                "FINANCIAL BREAKDOWN\nNone\n\n"
                "AFFECTED RECORDS\nNone\n\n"
                "RECOMMENDED NEXT CHECK\nProvide a valid entity target to investigate."
            )

        facts = context.facts
        target_type = context.target_entity_type or "Entity"
        target_id = context.target_entity_id or "Unknown"
        status = context.reconciliation_status

        # 1. Bank Amount Mismatch
        if "bank_delta" in facts.get("mathematical_breakdown", {}) and facts["mathematical_breakdown"]["bank_delta"] not in (None, "0.00", "0"):
            b_break = facts["mathematical_breakdown"]
            setl_amt = b_break.get("settlement_amount", "0.00")
            bank_amt = b_break.get("bank_amount", "0.00")
            bank_delta = b_break.get("bank_delta", "0.00")
            bank_id = facts.get("bank_entry_id", "Unknown")

            return (
                f"FINDING:\nSettlement {target_id} has a discrepancy with the observed bank statement.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] BankEntry {bank_id}\n[E3] BANK_AMOUNT_MISMATCH\n\n"
                f"FINANCIAL BREAKDOWN:\nSettlement Amount: ₹{setl_amt}\nBank Entry Amount: ₹{bank_amt}\nDifference: ₹{bank_delta}\n\n"
                f"AFFECTED RECORDS:\n- Settlement {target_id}\n- BankEntry {bank_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nInspect the bank statement transaction corresponding to UTR {facts.get('utr', 'N/A')} to resolve the ₹{bank_delta} delta."
            )

        # 2. Composition Shortfall / Missing Record
        if "composition_delta" in facts.get("mathematical_breakdown", {}) and facts["mathematical_breakdown"]["composition_delta"] not in (None, "0.00", "0"):
            b_break = facts["mathematical_breakdown"]
            setl_amt = b_break.get("settlement_amount", "0.00")
            calc_amt = b_break.get("calculated_component_total", "0.00")
            delta = b_break.get("composition_delta", "0.00")

            return (
                f"FINDING:\nSettlement {target_id} has a settlement composition mismatch between constituent records and settlement header.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] SETTLEMENT_COMPOSITION_MISMATCH\n\n"
                f"FINANCIAL BREAKDOWN:\nSettlement Amount: ₹{setl_amt}\nSum of Line Items: ₹{calc_amt}\nShortfall: ₹{delta}\n\n"
                f"AFFECTED RECORDS:\n- Settlement {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nVerify whether a constituent payment or refund transaction was omitted from the settlement batch."
            )

        # 3. Clean Reconciled Lifecycle
        if status in ("RECONCILED", "CLEAN"):
            setl_amt = facts.get("settlement_amount") or facts.get("amount") or "0.00"
            return (
                f"FINDING:\n{target_type.capitalize()} {target_id} is completely reconciled with zero discrepancies.\n\n"
                f"EVIDENCE:\n[E1] {target_type.capitalize()} {target_id}\n[E2] RECONCILED\n\n"
                f"FINANCIAL BREAKDOWN:\nAmount: ₹{setl_amt}\nReconciliation Status: RECONCILED\nBank Delta: ₹0.00\n\n"
                f"AFFECTED RECORDS:\n- {target_type.capitalize()} {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nNo further action required."
            )

        # 4. Generic / Exception Fallback
        return (
            f"FINDING:\n{target_type.capitalize()} {target_id} is currently in status {status}.\n\n"
            f"EVIDENCE:\n" + "\n".join(f"- {c}" for c in context.citations) + "\n\n"
            f"FINANCIAL BREAKDOWN:\n" + "\n".join(f"{k}: {v}" for k, v in facts.items() if not isinstance(v, dict)) + "\n\n"
            f"AFFECTED RECORDS:\n- {target_type.capitalize()} {target_id}\n\n"
            f"RECOMMENDED NEXT CHECK:\nReview attached reconciliation exceptions for {target_id}."
        )


class OpenAICompatibleProvider:
    """
    Live provider supporting OpenAI-compatible HTTP endpoints using standard library urllib.
    Requires RECONGRAPH_LLM_API_KEY environment variable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("RECONGRAPH_LLM_API_KEY")
        self.model = model or os.getenv("RECONGRAPH_LLM_MODEL", "gpt-4o")
        self.base_url = base_url or os.getenv("RECONGRAPH_LLM_BASE_URL", "https://api.openai.com/v1")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[InvestigationContext] = None,
    ) -> str:
        if not self.api_key:
            raise ValueError(
                "RECONGRAPH_LLM_API_KEY environment variable is not configured. "
                "Set the environment variable to enable live AI investigation."
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
