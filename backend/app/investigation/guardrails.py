"""
Security guardrails: Prompt injection defense, data exfiltration defense, and grounded answer validation.
"""

import re
from typing import List, Optional, Set, Tuple

from backend.app.investigation.context import InvestigationContext

# Forbidden phrases triggering prompt injection or exfiltration defense
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt",
    r"reveal (your )?instructions",
    r"api[ _]?key",
    r"environment variable",
    r"exfiltrate",
    r"admin override",
    r"bypass security",
    r"execute (shell|bash|python)",
]


class PromptInjectionGuard:
    """Detects and intercepts prompt injection attempts in operator queries."""

    @classmethod
    def check(cls, text: str) -> Tuple[bool, Optional[str]]:
        lower = text.lower()
        for pat in INJECTION_PATTERNS:
            if re.search(pat, lower):
                return False, "Security Notice: Your query contains instructions or tokens that violate system security policies."
        return True, None


class DataExfiltrationGuard:
    """Prevents leakage of sensitive environment variables, secrets, or internal instructions."""

    @classmethod
    def check(cls, text: str) -> Tuple[bool, Optional[str]]:
        lower = text.lower().replace("_", "").replace(" ", "")
        forbidden = ["secret", "apikey", "password", "systemprompt", "groundtruth", "anomalymanifest"]
        for term in forbidden:
            if term in lower:
                return False, "Security Notice: Access to internal secrets, system configurations, and benchmark truth is restricted."
        return True, None


class AnswerValidator:
    """
    Deterministically validates that all monetary figures and entity IDs in the generated response
    exist in the retrieved InvestigationContext.
    """

    @classmethod
    def validate(cls, answer: str, context: InvestigationContext) -> Tuple[bool, Optional[str]]:
        context_str = str(context.model_dump())

        # 1. Extract entity IDs (e.g. setl_12345, pay_67890, bank_111, merch_222, ord_333, ref_444, adj_555)
        entity_id_matches = re.findall(r"\b(setl_[a-zA-Z0-9_]+|pay_[a-zA-Z0-9_]+|bank_[a-zA-Z0-9_]+|merch_[a-zA-Z0-9_]+|ord_[a-zA-Z0-9_]+|ref_[a-zA-Z0-9_]+|adj_[a-zA-Z0-9_]+)\b", answer)

        for eid in entity_id_matches:
            if eid not in context_str:
                return False, f"Validation Failure: Mentioned entity ID '{eid}' is not present in retrieved context."

        # Remove entity IDs before checking monetary amounts to prevent ID substrings from triggering amount checks
        scrubbed_answer = re.sub(r"\b[a-z]+_[a-zA-Z0-9_]+\b", "", answer)

        # 2. Extract monetary amounts (e.g. ₹14,396, 14396.00, 250, 250.00)
        amount_matches = re.findall(r"(?:₹|\$)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)", scrubbed_answer)

        for amt_str in amount_matches:
            cleaned_num = amt_str.replace(",", "").strip()
            if not cleaned_num:
                continue

            # Ignore small structural counts
            if cleaned_num in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10") and "." not in amt_str:
                continue

            num_no_dec = cleaned_num.split(".")[0] if "." in cleaned_num else cleaned_num

            # Check if this monetary amount is anywhere in context
            if cleaned_num not in context_str and num_no_dec not in context_str:
                return False, f"Validation Failure: Mentioned amount '{amt_str}' is not supported by retrieved evidence context."

        return True, None
