"""
Provider abstraction and deterministic mock / live implementations for the AI Investigator.
"""

import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Tuple

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
    strictly from the retrieved InvestigationContext and deterministic financial rules.
    Contains zero hard-coded settlement IDs or static monetary amounts.
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
                "FINDING:\nNo evidence context was provided for investigation.\n\n"
                "EVIDENCE:\nNone\n\n"
                "FINANCIAL BREAKDOWN:\nNone\n\n"
                "AFFECTED RECORDS:\nNone\n\n"
                "RECOMMENDED NEXT CHECK:\nProvide a valid entity target to investigate."
            )

        facts = context.facts
        target_type = context.target_entity_type or "Entity"
        target_id = context.target_entity_id or "Unknown"
        status = context.reconciliation_status

        # Extract operator question from user prompt if available
        q_match = re.search(r"OPERATOR QUESTION:\s*(.*?)\s*RETRIEVED EVIDENCE CONTEXT:", user_prompt, re.DOTALL)
        q_text = q_match.group(1).strip().lower() if q_match else user_prompt.lower()

        # ---------------------------------------------------------------------
        # 1. Follow-up: "What payments contributed to this settlement?"
        # ---------------------------------------------------------------------
        if any(term in q_text for term in ["payments contributed", "what payments", "which payments", "contributed to this settlement", "payment contributions", "list payments"]):
            p_count = facts.get("payments_count", 0)
            p_net = facts.get("mathematical_breakdown", {}).get("payments_net_total") or facts.get("payments_net_total", "0.00")
            setl_amt = facts.get("settlement_amount", "0.00")
            const_payments = facts.get("constituent_payments", [])

            lines_breakdown = [
                f"Payments Count: {p_count}",
                f"Payments Net Total: ₹{p_net}",
                f"Settlement Amount: ₹{setl_amt}",
            ]
            aff_records = [f"- Settlement {target_id}"]
            if const_payments:
                lines_breakdown.append("Constituent Payments:")
                for p in const_payments[:8]:
                    pid = p.get("entity_id")
                    pamt = p.get("amount", "0.00")
                    lines_breakdown.append(f"  - {pid}: ₹{pamt}")
                    aff_records.append(f"- Payment {pid}")
            elif facts.get("connected_nodes"):
                for n in facts.get("connected_nodes", []):
                    if isinstance(n, str) and n.startswith("payment:"):
                        aff_records.append(f"- Payment {n.split(':', 1)[1]}")

            return (
                f"FINDING:\nSettlement {target_id} is composed of {p_count} constituent payment transaction(s) with an aggregated net total of ₹{p_net}.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] Constituent Payments ({p_count})\n[E3] SETTLEMENT_TRANSACTIONS\n\n"
                f"FINANCIAL BREAKDOWN:\n" + "\n".join(lines_breakdown) + "\n\n"
                f"AFFECTED RECORDS:\n" + "\n".join(aff_records[:10]) + "\n\n"
                f"RECOMMENDED NEXT CHECK:\nInspect individual payment transactions or corresponding merchant orders for itemized audit."
            )

        # ---------------------------------------------------------------------
        # 2. Follow-up: "Are there any refunds affecting this settlement?"
        # ---------------------------------------------------------------------
        if any(term in q_text for term in ["refund", "refunds", "refund debit"]):
            r_count = facts.get("refunds_count", 0)
            r_net = facts.get("mathematical_breakdown", {}).get("refunds_net_total") or facts.get("refunds_net_total", "0.00")
            const_refunds = facts.get("constituent_refunds", [])

            if r_count > 0 or (r_net and r_net not in ("0", "0.00", "-0.00")):
                lines_breakdown = [
                    f"Refund Count: {r_count}",
                    f"Refunds Net Total: ₹{r_net}",
                ]
                aff_records = [f"- Settlement {target_id}"]
                for r in const_refunds:
                    rid = r.get("entity_id")
                    ramt = r.get("amount", "0.00")
                    lines_breakdown.append(f"  - {rid}: ₹{ramt}")
                    aff_records.append(f"- Refund {rid}")

                return (
                    f"FINDING:\nSettlement {target_id} includes {r_count} refund deduction(s) totaling ₹{r_net} deducted from the payout.\n\n"
                    f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] Refund Records ({r_count})\n\n"
                    f"FINANCIAL BREAKDOWN:\n" + "\n".join(lines_breakdown) + "\n\n"
                    f"AFFECTED RECORDS:\n" + "\n".join(aff_records) + "\n\n"
                    f"RECOMMENDED NEXT CHECK:\nVerify refund authorization reference against gateway customer dispute ledger."
                )
            else:
                return (
                    f"FINDING:\nNo refund debits were observed affecting settlement {target_id}. The constituent transaction batch contains 0 refunds.\n\n"
                    f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] ZERO_REFUNDS_OBSERVED\n\n"
                    f"FINANCIAL BREAKDOWN:\nRefund Count: 0\nRefunds Net Total: ₹0.00\n\n"
                    f"AFFECTED RECORDS:\n- Settlement {target_id}\n\n"
                    f"RECOMMENDED NEXT CHECK:\nNo refund reconciliation action required."
                )

        # ---------------------------------------------------------------------
        # 3. Follow-up: "How was the settlement amount calculated?"
        # ---------------------------------------------------------------------
        if any(term in q_text for term in ["calculated", "how was", "calculation", "formula", "breakdown", "composition equation"]):
            m_break = facts.get("mathematical_breakdown", {})
            p_net = m_break.get("payments_net_total", "0.00")
            r_net = m_break.get("refunds_net_total", "0.00")
            a_net = m_break.get("adjustments_net_total", "0.00")
            t_net = m_break.get("transfers_net_total", "0.00")
            calc_tot = m_break.get("calculated_component_total", facts.get("settlement_amount", "0.00"))
            setl_amt = m_break.get("settlement_amount", facts.get("settlement_amount", "0.00"))
            comp_delta = m_break.get("composition_delta", "0.00")

            return (
                f"FINDING:\nSettlement {target_id} amount of ₹{setl_amt} is calculated from constituent payments (₹{p_net}), refunds (₹{r_net}), adjustments (₹{a_net}), and transfers (₹{t_net}), yielding calculated component total ₹{calc_tot}.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] Constituent Line Items\n[E3] SETTLEMENT_COMPOSITION\n\n"
                f"FINANCIAL BREAKDOWN:\nPayments Net Total: ₹{p_net}\nRefunds Net Total: ₹{r_net}\nAdjustments Net Total: ₹{a_net}\nTransfers Net Total: ₹{t_net}\nCalculated Component Total: ₹{calc_tot}\nSettlement Amount: ₹{setl_amt}\nComposition Delta: ₹{comp_delta}\n\n"
                f"AFFECTED RECORDS:\n- Settlement {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nVerify all constituent settlement transactions against gateway batch report."
            )

        # ---------------------------------------------------------------------
        # 4. Payment Tracing / Payment Specific Investigation
        # ---------------------------------------------------------------------
        if target_type == "payment" or target_id.startswith("pay_") or "trace" in q_text:
            pay_amt = facts.get("amount", "0.00")
            fee_amt = facts.get("fee", "0.00")
            tax_amt = facts.get("tax", "0.00")
            net_amt = facts.get("net_amount", pay_amt)
            order_id = facts.get("order_id", "Unknown")
            setl_id = facts.get("settlement_id", "Pending")
            utr = facts.get("utr", "N/A")
            pay_status = facts.get("status", "captured")

            aff = [f"- Payment {target_id}"]
            if order_id and order_id != "Unknown":
                aff.append(f"- Order {order_id}")
            if setl_id and setl_id != "Pending":
                aff.append(f"- Settlement {setl_id}")

            return (
                f"FINDING:\nPayment {target_id} for ₹{pay_amt} is linked to Order {order_id} and settled under Settlement {setl_id} (UTR: {utr}). It is currently {'RECONCILED' if status in ('CLEAN', 'RECONCILED') else status}.\n\n"
                f"EVIDENCE:\n[E1] Payment {target_id}\n[E2] Order {order_id}\n[E3] Settlement {setl_id}\n\n"
                f"FINANCIAL BREAKDOWN:\nPayment Gross Amount: ₹{pay_amt}\nFee: ₹{fee_amt}\nTax: ₹{tax_amt}\nNet Payout: ₹{net_amt}\nPayment Status: {pay_status}\nReconciliation Status: {status}\n\n"
                f"AFFECTED RECORDS:\n" + "\n".join(aff) + "\n\n"
                f"RECOMMENDED NEXT CHECK:\nVerify settlement disbursement in bank statement under UTR {utr}."
            )

        # ---------------------------------------------------------------------
        # 5. Bank Amount Mismatch
        # ---------------------------------------------------------------------
        if "bank_delta" in facts.get("mathematical_breakdown", {}) and facts["mathematical_breakdown"]["bank_delta"] not in (None, "0.00", "0", "0.0", "-0.00"):
            b_break = facts["mathematical_breakdown"]
            setl_amt = b_break.get("settlement_amount", "0.00")
            bank_amt = b_break.get("bank_amount", "0.00")
            bank_delta = b_break.get("bank_delta", "0.00")
            bank_id = facts.get("bank_entry_id", "Unknown")
            utr_val = facts.get("utr", "N/A")

            return (
                f"FINDING:\nSettlement {target_id} has a discrepancy of ₹{bank_delta} with the observed bank statement. Observed settlement amount is ₹{setl_amt} while the bank entry is ₹{bank_amt}.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] BankEntry {bank_id}\n[E3] BANK_AMOUNT_MISMATCH\n\n"
                f"FINANCIAL BREAKDOWN:\nSettlement Amount: ₹{setl_amt}\nBank Entry Amount: ₹{bank_amt}\nDifference: ₹{bank_delta}\n\n"
                f"AFFECTED RECORDS:\n- Settlement {target_id}\n- BankEntry {bank_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nInspect the bank statement transaction corresponding to UTR {utr_val} to resolve the ₹{bank_delta} delta."
            )

        # ---------------------------------------------------------------------
        # 6. Composition Shortfall / Missing Record
        # ---------------------------------------------------------------------
        if "composition_delta" in facts.get("mathematical_breakdown", {}) and facts["mathematical_breakdown"]["composition_delta"] not in (None, "0.00", "0", "0.0", "-0.00"):
            b_break = facts["mathematical_breakdown"]
            setl_amt = b_break.get("settlement_amount", "0.00")
            calc_amt = b_break.get("calculated_component_total", "0.00")
            delta = b_break.get("composition_delta", "0.00")

            return (
                f"FINDING:\nSettlement {target_id} has a settlement composition mismatch of ₹{delta} between constituent records and settlement header.\n\n"
                f"EVIDENCE:\n[E1] Settlement {target_id}\n[E2] SETTLEMENT_COMPOSITION_MISMATCH\n\n"
                f"FINANCIAL BREAKDOWN:\nSettlement Amount: ₹{setl_amt}\nSum of Line Items: ₹{calc_amt}\nShortfall: ₹{delta}\n\n"
                f"AFFECTED RECORDS:\n- Settlement {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nVerify whether a constituent payment or refund transaction was omitted from the settlement batch."
            )

        # ---------------------------------------------------------------------
        # 7. Clean Reconciled Lifecycle
        # ---------------------------------------------------------------------
        if status in ("RECONCILED", "CLEAN"):
            setl_amt = facts.get("settlement_amount") or facts.get("amount") or "0.00"
            return (
                f"FINDING:\n{target_type.capitalize()} {target_id} is completely reconciled with zero discrepancies.\n\n"
                f"EVIDENCE:\n[E1] {target_type.capitalize()} {target_id}\n[E2] RECONCILED\n\n"
                f"FINANCIAL BREAKDOWN:\nAmount: ₹{setl_amt}\nReconciliation Status: RECONCILED\nBank Delta: ₹0.00\n\n"
                f"AFFECTED RECORDS:\n- {target_type.capitalize()} {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nNo further action required."
            )

        # ---------------------------------------------------------------------
        # 8. Specific Exception Rule from Evidence
        # ---------------------------------------------------------------------
        if context.evidence:
            first_ev = context.evidence[0]
            rule_code = first_ev.get("rule_code", "EXCEPTION")
            diff = first_ev.get("difference", "0.00")
            exp = first_ev.get("expected_value", "N/A")
            obs = first_ev.get("observed_value", "N/A")

            return (
                f"FINDING:\n{target_type.capitalize()} {target_id} failed reconciliation rule {rule_code}. Expected {exp} vs Observed {obs} with difference {diff}.\n\n"
                f"EVIDENCE:\n[E1] {target_type.capitalize()} {target_id}\n[E2] {rule_code}\n\n"
                f"FINANCIAL BREAKDOWN:\nExpected Value: {exp}\nObserved Value: {obs}\nDifference: {diff}\n\n"
                f"AFFECTED RECORDS:\n- {target_type.capitalize()} {target_id}\n\n"
                f"RECOMMENDED NEXT CHECK:\nReview source gateway logs and bank statement details for {target_id}."
            )

        # ---------------------------------------------------------------------
        # 9. Generic / Fallback Grounded Explanation
        # ---------------------------------------------------------------------
        citations_str = "\n".join(f"- {c}" for c in context.citations) if context.citations else f"[E1] {target_type.capitalize()} {target_id}"
        breakdown_str = "\n".join(f"{k}: {v}" for k, v in facts.items() if not isinstance(v, (dict, list)))
        if not breakdown_str:
            breakdown_str = f"Status: {status}"

        return (
            f"FINDING:\n{target_type.capitalize()} {target_id} is currently in status {status}.\n\n"
            f"EVIDENCE:\n{citations_str}\n\n"
            f"FINANCIAL BREAKDOWN:\n{breakdown_str}\n\n"
            f"AFFECTED RECORDS:\n- {target_type.capitalize()} {target_id}\n\n"
            f"RECOMMENDED NEXT CHECK:\nReview attached reconciliation evidence for {target_id}."
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


def get_investigation_provider() -> Tuple[LLMProvider, str]:
    """
    Returns the configured investigation provider and its provider_mode string.
    Defaults to DeterministicMockProvider ('deterministic') when no API key is set.
    """
    api_key = os.getenv("RECONGRAPH_LLM_API_KEY")
    if api_key and api_key.strip():
        return OpenAICompatibleProvider(), "live"
    return DeterministicMockProvider(), "deterministic"
