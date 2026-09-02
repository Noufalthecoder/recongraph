"""
Settlement composition and line-item arithmetic validation.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from backend.app.models.common import MoneyDecimal
from backend.app.models.settlement import Settlement
from backend.app.models.settlement_transaction import (
    SettlementTransaction,
    SettlementTransactionType,
)
from backend.app.reconciliation.exceptions import ExceptionSeverity, ReconciliationExceptionType
from backend.app.reconciliation.models import (
    EntityReference,
    ReconciliationConfig,
    ReconciliationException,
    ReconciliationMatch,
)
from backend.app.reconciliation.rules import (
    RULE_LINE_ITEM_ARITHMETIC,
    RULE_SETTLEMENT_COMPOSITION_SUM,
    build_evidence,
    build_exception,
    build_match,
)


class SettlementCompositionValidator:
    """
    Validates that a Settlement's aggregate amount equals the net sum of all
    its constituent SettlementTransactions, and that each constituent line-item
    satisfies exact arithmetic constraints.
    """

    @classmethod
    def validate_line_items(
        cls,
        stxns: List[SettlementTransaction],
        config: ReconciliationConfig,
        counter: Dict[str, int],
    ) -> List[ReconciliationException]:
        exceptions: List[ReconciliationException] = []

        if not config.validate_component_fees_tax:
            return exceptions

        for stxn in stxns:
            if stxn.type == SettlementTransactionType.CREDIT:
                expected_net = (stxn.amount - stxn.fee - stxn.tax).quantize(Decimal("0.01"))
            else:  # DEBIT
                expected_net = (-(stxn.amount + stxn.fee + stxn.tax)).quantize(Decimal("0.01"))

            diff = abs(stxn.net_amount - expected_net)
            if diff > config.tolerance:
                counter["exc"] += 1
                exc_id = f"exc_{counter['exc']:04d}"
                stxn_ref = EntityReference(
                    entity_type="settlement_transaction",
                    entity_id=stxn.settlement_txn_id,
                )
                evidence = build_evidence(
                    rule_code=RULE_LINE_ITEM_ARITHMETIC,
                    rule_description=(
                        f"SettlementTransaction {stxn.settlement_txn_id} net_amount ({stxn.net_amount}) "
                        f"does not match expected net amount ({expected_net}) based on amount ({stxn.amount}), "
                        f"fee ({stxn.fee}), and tax ({stxn.tax})."
                    ),
                    primary_entity=stxn_ref,
                    expected_value=str(expected_net),
                    observed_value=str(stxn.net_amount),
                    difference=stxn.net_amount - expected_net,
                    details={
                        "settlement_txn_id": stxn.settlement_txn_id,
                        "type": str(stxn.type),
                        "amount": str(stxn.amount),
                        "fee": str(stxn.fee),
                        "tax": str(stxn.tax),
                    },
                )
                exceptions.append(
                    build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.LINE_ITEM_ARITHMETIC_MISMATCH,
                        severity=ExceptionSeverity.CRITICAL,
                        primary_entity=stxn_ref,
                        rule_code=RULE_LINE_ITEM_ARITHMETIC,
                        expected_value=str(expected_net),
                        observed_value=str(stxn.net_amount),
                        difference=stxn.net_amount - expected_net,
                        evidence=evidence,
                    )
                )

        return exceptions

    @classmethod
    def validate_composition(
        cls,
        settlement: Settlement,
        stxns: List[SettlementTransaction],
        config: ReconciliationConfig,
        counter: Dict[str, int],
    ) -> Tuple[Decimal, List[ReconciliationMatch], List[ReconciliationException]]:
        """
        Validates the settlement equation:
        Settlement.amount == SUM(stxn.net_amount)
        """
        matches: List[ReconciliationMatch] = []
        exceptions: List[ReconciliationException] = []

        setl_ref = EntityReference(
            entity_type="settlement",
            entity_id=settlement.settlement_id,
        )

        # 1. Validate constituent line items
        line_item_exceptions = cls.validate_line_items(stxns, config, counter)
        exceptions.extend(line_item_exceptions)

        # 2. Compute component sums
        calculated_net_total = sum(
            (st.net_amount for st in stxns),
            Decimal("0.00")
        ).quantize(Decimal("0.01"))

        calculated_fee_total = sum(
            (st.fee for st in stxns),
            Decimal("0.00")
        ).quantize(Decimal("0.01"))

        calculated_tax_total = sum(
            (st.tax for st in stxns),
            Decimal("0.00")
        ).quantize(Decimal("0.01"))

        # Breakdown by entity type for rich evidence
        breakdown_by_type: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for st in stxns:
            breakdown_by_type[str(st.entity_type)] += st.net_amount

        diff = settlement.amount - calculated_net_total
        abs_diff = abs(diff)

        related_refs = [
            EntityReference(entity_type="settlement_transaction", entity_id=st.settlement_txn_id)
            for st in sorted(stxns, key=lambda x: x.settlement_txn_id)
        ]

        if abs_diff <= config.tolerance:
            counter["match"] += 1
            match_id = f"match_{counter['match']:04d}"
            evidence = build_evidence(
                rule_code=RULE_SETTLEMENT_COMPOSITION_SUM,
                rule_description="Settlement amount equals the sum of constituent transaction net amounts.",
                primary_entity=setl_ref,
                related_entities=related_refs,
                expected_value=str(settlement.amount),
                observed_value=str(calculated_net_total),
                difference=diff,
                details={
                    "settlement_id": settlement.settlement_id,
                    "line_item_count": len(stxns),
                    "calculated_component_total": str(calculated_net_total),
                    "observed_settlement_amount": str(settlement.amount),
                    "fees_total": str(calculated_fee_total),
                    "tax_total": str(calculated_tax_total),
                    "breakdown": {k: str(v) for k, v in sorted(breakdown_by_type.items())},
                },
            )
            matches.append(
                build_match(
                    match_id=match_id,
                    match_type=RULE_SETTLEMENT_COMPOSITION_SUM,
                    entities=[setl_ref] + related_refs,
                    evidence=evidence,
                )
            )
        else:
            counter["exc"] += 1
            exc_id = f"exc_{counter['exc']:04d}"
            evidence = build_evidence(
                rule_code=RULE_SETTLEMENT_COMPOSITION_SUM,
                rule_description=(
                    f"Settlement {settlement.settlement_id} amount ({settlement.amount}) does not equal "
                    f"the sum of constituent SettlementTransaction net amounts ({calculated_net_total}). "
                    f"Difference: {diff}."
                ),
                primary_entity=setl_ref,
                related_entities=related_refs,
                expected_value=str(calculated_net_total),
                observed_value=str(settlement.amount),
                difference=diff,
                details={
                    "settlement_id": settlement.settlement_id,
                    "line_item_count": len(stxns),
                    "calculated_component_total": str(calculated_net_total),
                    "observed_settlement_amount": str(settlement.amount),
                    "difference": str(diff),
                    "fees_total": str(calculated_fee_total),
                    "tax_total": str(calculated_tax_total),
                    "constituent_txn_ids": [st.settlement_txn_id for st in sorted(stxns, key=lambda x: x.settlement_txn_id)],
                    "breakdown": {k: str(v) for k, v in sorted(breakdown_by_type.items())},
                },
            )
            exceptions.append(
                build_exception(
                    exception_id=exc_id,
                    exception_type=ReconciliationExceptionType.SETTLEMENT_COMPOSITION_MISMATCH,
                    severity=ExceptionSeverity.CRITICAL,
                    primary_entity=setl_ref,
                    related_entities=related_refs,
                    rule_code=RULE_SETTLEMENT_COMPOSITION_SUM,
                    expected_value=str(calculated_net_total),
                    observed_value=str(settlement.amount),
                    difference=diff,
                    evidence=evidence,
                )
            )

        return calculated_net_total, matches, exceptions
