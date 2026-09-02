"""
Deterministic rule definitions, constants, and evidence builders.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.models.common import MoneyDecimal
from backend.app.reconciliation.exceptions import ExceptionSeverity, ReconciliationExceptionType
from backend.app.reconciliation.models import (
    EntityReference,
    ReconciliationEvidence,
    ReconciliationException,
    ReconciliationMatch,
    UnmatchedRecord,
)

# Rule Codes
RULE_SETTLEMENT_BANK_EXACT = "SETTLEMENT_BANK_EXACT_MATCH"
RULE_SETTLEMENT_BANK_AMOUNT_MISMATCH = "SETTLEMENT_BANK_AMOUNT_MISMATCH"
RULE_SETTLEMENT_BANK_IDENTIFIER_MISMATCH = "SETTLEMENT_BANK_IDENTIFIER_MISMATCH"
RULE_SETTLEMENT_COMPOSITION_SUM = "SETTLEMENT_COMPOSITION_SUM"
RULE_LINE_ITEM_ARITHMETIC = "LINE_ITEM_ARITHMETIC"
RULE_MISSING_BANK_ENTRY = "MISSING_BANK_ENTRY"
RULE_UNMATCHED_BANK_ENTRY = "UNMATCHED_BANK_ENTRY"
RULE_DUPLICATE_PRIMARY_KEY = "DUPLICATE_PRIMARY_KEY"
RULE_DUPLICATE_SETTLEMENT_PARTICIPATION = "DUPLICATE_SETTLEMENT_PARTICIPATION"
RULE_DUPLICATE_UTR = "DUPLICATE_UTR"
RULE_MISSING_FOREIGN_KEY = "MISSING_FOREIGN_KEY"
RULE_CROSS_REFERENCE_MISMATCH = "CROSS_REFERENCE_MISMATCH"
RULE_REFUND_LIMIT = "REFUND_LIMIT_EXCEEDED"
RULE_PAYMENT_SETTLEMENT_LINK = "PAYMENT_SETTLEMENT_LINK"
RULE_REFUND_SETTLEMENT_LINK = "REFUND_SETTLEMENT_LINK"
RULE_ADJUSTMENT_SETTLEMENT_LINK = "ADJUSTMENT_SETTLEMENT_LINK"
RULE_ORDER_PAYMENT_LINK = "ORDER_PAYMENT_LINK"


def build_evidence(
    rule_code: str,
    rule_description: str,
    primary_entity: EntityReference,
    related_entities: Optional[List[EntityReference]] = None,
    expected_value: Optional[str] = None,
    observed_value: Optional[str] = None,
    difference: Optional[MoneyDecimal] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ReconciliationEvidence:
    return ReconciliationEvidence(
        rule_code=rule_code,
        rule_description=rule_description,
        primary_entity=primary_entity,
        related_entities=related_entities or [],
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        details=details or {},
    )


def build_match(
    match_id: str,
    match_type: str,
    entities: List[EntityReference],
    evidence: ReconciliationEvidence,
) -> ReconciliationMatch:
    return ReconciliationMatch(
        match_id=match_id,
        match_type=match_type,
        entities=entities,
        evidence=evidence,
    )


def build_exception(
    exception_id: str,
    exception_type: ReconciliationExceptionType,
    severity: ExceptionSeverity,
    primary_entity: EntityReference,
    rule_code: str,
    evidence: ReconciliationEvidence,
    related_entities: Optional[List[EntityReference]] = None,
    expected_value: Optional[str] = None,
    observed_value: Optional[str] = None,
    difference: Optional[MoneyDecimal] = None,
) -> ReconciliationException:
    return ReconciliationException(
        exception_id=exception_id,
        exception_type=exception_type,
        severity=severity,
        primary_entity=primary_entity,
        related_entities=related_entities or (evidence.related_entities if evidence else []),
        rule_code=rule_code,
        expected_value=expected_value or (evidence.expected_value if evidence else None),
        observed_value=observed_value or (evidence.observed_value if evidence else None),
        difference=difference if difference is not None else (evidence.difference if evidence else None),
        evidence=evidence,
    )


def build_unmatched(
    entity: EntityReference,
    reason: str,
    details: Optional[Dict[str, Any]] = None,
) -> UnmatchedRecord:
    return UnmatchedRecord(
        entity=entity,
        reason=reason,
        details=details or {},
    )
