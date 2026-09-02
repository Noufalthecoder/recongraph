"""
Reconciliation exception taxonomy and severity models.
"""

from enum import Enum


class ReconciliationExceptionType(str, Enum):
    """Authoritative taxonomy of deterministic reconciliation exceptions."""

    # 1. Amount & Arithmetic Mismatches
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    SETTLEMENT_COMPOSITION_MISMATCH = "SETTLEMENT_COMPOSITION_MISMATCH"
    BANK_AMOUNT_MISMATCH = "BANK_AMOUNT_MISMATCH"
    LINE_ITEM_ARITHMETIC_MISMATCH = "LINE_ITEM_ARITHMETIC_MISMATCH"

    # 2. Identifier & Reference Mismatches
    IDENTIFIER_MISMATCH = "IDENTIFIER_MISMATCH"
    CROSS_REFERENCE_MISMATCH = "CROSS_REFERENCE_MISMATCH"
    DUPLICATE_UTR = "DUPLICATE_UTR"

    # 3. Structural & Referential Integrity
    MISSING_RECORD = "MISSING_RECORD"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    INVALID_RELATIONSHIP = "INVALID_RELATIONSHIP"

    # 4. Lifecycle & Domain State Invariants
    INVALID_FINANCIAL_STATE = "INVALID_FINANCIAL_STATE"
    REFUND_EXCEEDS_PAYMENT = "REFUND_EXCEEDS_PAYMENT"

    # 5. Unmatched Records
    UNMATCHED_RECORD = "UNMATCHED_RECORD"


class ExceptionSeverity(str, Enum):
    """Severity classification for exceptions and audit prioritization."""

    CRITICAL = "CRITICAL"  # Ledger imbalance / amount mismatch / composition failure
    ERROR = "ERROR"        # Missing reference / duplicate record / invalid state
    WARNING = "WARNING"    # Unmatched bank entry / pending entity
    INFO = "INFO"          # Informational / non-blocking diagnostic
