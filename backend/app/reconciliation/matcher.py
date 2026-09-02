"""
Deterministic multi-pass matcher and referential validator.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from backend.app.models.bank_entry import BankEntry
from backend.app.models.common import MoneyDecimal
from backend.app.models.settlement import Settlement, SettlementStatus
from backend.app.models.settlement_transaction import (
    SettlementTransaction,
    SettlementTransactionEntityType,
)
from backend.app.reconciliation.exceptions import ExceptionSeverity, ReconciliationExceptionType
from backend.app.reconciliation.indexer import NormalizedObservationIndex
from backend.app.reconciliation.models import (
    EntityReference,
    ReconciliationConfig,
    ReconciliationException,
    ReconciliationMatch,
    UnmatchedRecord,
)
from backend.app.reconciliation.rules import (
    RULE_ADJUSTMENT_SETTLEMENT_LINK,
    RULE_CROSS_REFERENCE_MISMATCH,
    RULE_DUPLICATE_PRIMARY_KEY,
    RULE_DUPLICATE_SETTLEMENT_PARTICIPATION,
    RULE_DUPLICATE_UTR,
    RULE_MISSING_BANK_ENTRY,
    RULE_MISSING_FOREIGN_KEY,
    RULE_ORDER_PAYMENT_LINK,
    RULE_PAYMENT_SETTLEMENT_LINK,
    RULE_REFUND_LIMIT,
    RULE_REFUND_SETTLEMENT_LINK,
    RULE_SETTLEMENT_BANK_AMOUNT_MISMATCH,
    RULE_SETTLEMENT_BANK_EXACT,
    RULE_SETTLEMENT_BANK_IDENTIFIER_MISMATCH,
    RULE_UNMATCHED_BANK_ENTRY,
    build_evidence,
    build_exception,
    build_match,
    build_unmatched,
)


class DeterministicMatcher:
    """
    Executes deterministic duplicate detection, referential validation,
    and multi-pass Settlement <-> BankEntry matching.
    """

    def __init__(
        self,
        index: NormalizedObservationIndex,
        config: ReconciliationConfig,
        counter: Dict[str, int],
    ):
        self.index = index
        self.config = config
        self.counter = counter

    def detect_duplicates(self) -> List[ReconciliationException]:
        """Detects primary key collisions, duplicate participations, and duplicate UTRs."""
        exceptions: List[ReconciliationException] = []

        # 1. Primary key collisions across all collections
        collections = [
            ("merchant", self.index.merchants_by_id),
            ("order", self.index.orders_by_id),
            ("payment", self.index.payments_by_id),
            ("refund", self.index.refunds_by_id),
            ("adjustment", self.index.adjustments_by_id),
            ("settlement", self.index.settlements_by_id),
            ("settlement_transaction", self.index.stxns_by_id),
            ("bank_entry", self.index.bank_entries_by_id),
        ]

        for entity_name, entity_dict in collections:
            for entity_id in sorted(entity_dict.keys()):
                records = entity_dict[entity_id]
                if len(records) > 1:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    entity_ref = EntityReference(entity_type=entity_name, entity_id=entity_id)
                    evidence = build_evidence(
                        rule_code=RULE_DUPLICATE_PRIMARY_KEY,
                        rule_description=f"Duplicate primary key '{entity_id}' found {len(records)} times in '{entity_name}' collection.",
                        primary_entity=entity_ref,
                        observed_value=f"count={len(records)}",
                        details={"occurrences": len(records), "entity_type": entity_name, "entity_id": entity_id},
                    )
                    exceptions.append(
                        build_exception(
                            exception_id=exc_id,
                            exception_type=ReconciliationExceptionType.DUPLICATE_RECORD,
                            severity=ExceptionSeverity.ERROR,
                            primary_entity=entity_ref,
                            rule_code=RULE_DUPLICATE_PRIMARY_KEY,
                            evidence=evidence,
                        )
                    )

        # 2. Duplicate settlement participation
        for target_key in sorted(self.index.stxns_by_target_entity.keys(), key=lambda k: (k[0], k[1])):
            stxns = self.index.stxns_by_target_entity[target_key]
            if len(stxns) > 1:
                entity_type, entity_id = target_key
                self.counter["exc"] += 1
                exc_id = f"exc_{self.counter['exc']:04d}"
                primary_ref = EntityReference(entity_type=entity_type, entity_id=entity_id)
                related_refs = [
                    EntityReference(entity_type="settlement_transaction", entity_id=st.settlement_txn_id)
                    for st in sorted(stxns, key=lambda s: s.settlement_txn_id)
                ]
                evidence = build_evidence(
                    rule_code=RULE_DUPLICATE_SETTLEMENT_PARTICIPATION,
                    rule_description=f"Entity ({entity_type}, {entity_id}) is referenced by multiple settlement transactions ({len(stxns)}).",
                    primary_entity=primary_ref,
                    related_entities=related_refs,
                    details={
                        "settlement_txn_ids": [st.settlement_txn_id for st in sorted(stxns, key=lambda s: s.settlement_txn_id)],
                        "settlement_ids": [st.settlement_id for st in sorted(stxns, key=lambda s: s.settlement_txn_id)],
                    },
                )
                exceptions.append(
                    build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.DUPLICATE_RECORD,
                        severity=ExceptionSeverity.ERROR,
                        primary_entity=primary_ref,
                        related_entities=related_refs,
                        rule_code=RULE_DUPLICATE_SETTLEMENT_PARTICIPATION,
                        evidence=evidence,
                    )
                )

        # 3. Duplicate UTR in BankEntries
        for utr in sorted(self.index.bank_entries_by_utr.keys()):
            bank_entries = self.index.bank_entries_by_utr[utr]
            if len(bank_entries) > 1:
                self.counter["exc"] += 1
                exc_id = f"exc_{self.counter['exc']:04d}"
                primary_ref = EntityReference(entity_type="bank_entry", entity_id=bank_entries[0].bank_entry_id)
                related_refs = [
                    EntityReference(entity_type="bank_entry", entity_id=b.bank_entry_id)
                    for b in sorted(bank_entries[1:], key=lambda x: x.bank_entry_id)
                ]
                evidence = build_evidence(
                    rule_code=RULE_DUPLICATE_UTR,
                    rule_description=f"Duplicate UTR '{utr}' observed on {len(bank_entries)} bank entries.",
                    primary_entity=primary_ref,
                    related_entities=related_refs,
                    observed_value=utr,
                    details={"utr": utr, "bank_entry_ids": [b.bank_entry_id for b in bank_entries]},
                )
                exceptions.append(
                    build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.DUPLICATE_UTR,
                        severity=ExceptionSeverity.ERROR,
                        primary_entity=primary_ref,
                        related_entities=related_refs,
                        rule_code=RULE_DUPLICATE_UTR,
                        evidence=evidence,
                    )
                )

        return exceptions

    def validate_referential_integrity(self) -> Tuple[List[ReconciliationMatch], List[ReconciliationException]]:
        """Validates all entity foreign keys and domain lifecycle constraints."""
        matches: List[ReconciliationMatch] = []
        exceptions: List[ReconciliationException] = []

        # 1. Payment -> Order validation
        for payment_id in sorted(self.index.payments_by_id.keys()):
            for payment in self.index.payments_by_id[payment_id]:
                pay_ref = EntityReference(entity_type="payment", entity_id=payment.payment_id)
                order = self.index.get_order(payment.order_id)
                if order is None:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_MISSING_FOREIGN_KEY,
                        rule_description=f"Payment {payment.payment_id} references non-existent order {payment.order_id}.",
                        primary_entity=pay_ref,
                        expected_value=payment.order_id,
                        observed_value=None,
                        details={"payment_id": payment.payment_id, "missing_order_id": payment.order_id},
                    )
                    exceptions.append(
                        build_exception(
                            exception_id=exc_id,
                            exception_type=ReconciliationExceptionType.MISSING_RECORD,
                            severity=ExceptionSeverity.ERROR,
                            primary_entity=pay_ref,
                            rule_code=RULE_MISSING_FOREIGN_KEY,
                            evidence=evidence,
                        )
                    )
                else:
                    self.counter["match"] += 1
                    match_id = f"match_{self.counter['match']:04d}"
                    order_ref = EntityReference(entity_type="order", entity_id=order.order_id)
                    evidence = build_evidence(
                        rule_code=RULE_ORDER_PAYMENT_LINK,
                        rule_description="Payment successfully linked to authoritative Order.",
                        primary_entity=pay_ref,
                        related_entities=[order_ref],
                        details={"payment_id": payment.payment_id, "order_id": order.order_id},
                    )
                    matches.append(
                        build_match(
                            match_id=match_id,
                            match_type=RULE_ORDER_PAYMENT_LINK,
                            entities=[pay_ref, order_ref],
                            evidence=evidence,
                        )
                    )

        # 2. Refund -> Payment validation & Cumulative Refund Limit
        refunds_by_payment: Dict[str, List] = {}
        for refund_id in sorted(self.index.refunds_by_id.keys()):
            for refund in self.index.refunds_by_id[refund_id]:
                rfnd_ref = EntityReference(entity_type="refund", entity_id=refund.refund_id)
                payment = self.index.get_payment(refund.payment_id)
                if payment is None:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_MISSING_FOREIGN_KEY,
                        rule_description=f"Refund {refund.refund_id} references non-existent payment {refund.payment_id}.",
                        primary_entity=rfnd_ref,
                        expected_value=refund.payment_id,
                        observed_value=None,
                        details={"refund_id": refund.refund_id, "missing_payment_id": refund.payment_id},
                    )
                    exceptions.append(
                        build_exception(
                            exception_id=exc_id,
                            exception_type=ReconciliationExceptionType.MISSING_RECORD,
                            severity=ExceptionSeverity.ERROR,
                            primary_entity=rfnd_ref,
                            rule_code=RULE_MISSING_FOREIGN_KEY,
                            evidence=evidence,
                        )
                    )
                else:
                    refunds_by_payment.setdefault(payment.payment_id, []).append(refund)

        # Cumulative refund sum validation
        for payment_id in sorted(refunds_by_payment.keys()):
            payment = self.index.get_payment(payment_id)
            if payment is None:
                continue
            r_list = refunds_by_payment[payment_id]
            total_refunded = sum((r.amount for r in r_list), Decimal("0.00")).quantize(Decimal("0.01"))
            pay_ref = EntityReference(entity_type="payment", entity_id=payment.payment_id)
            related_rfnd_refs = [
                EntityReference(entity_type="refund", entity_id=r.refund_id)
                for r in sorted(r_list, key=lambda x: x.refund_id)
            ]

            if total_refunded > payment.amount:
                self.counter["exc"] += 1
                exc_id = f"exc_{self.counter['exc']:04d}"
                diff = total_refunded - payment.amount
                evidence = build_evidence(
                    rule_code=RULE_REFUND_LIMIT,
                    rule_description=(
                        f"Cumulative refund total ({total_refunded}) exceeds original payment amount ({payment.amount}) "
                        f"for payment {payment.payment_id}."
                    ),
                    primary_entity=pay_ref,
                    related_entities=related_rfnd_refs,
                    expected_value=str(payment.amount),
                    observed_value=str(total_refunded),
                    difference=diff,
                    details={
                        "payment_id": payment.payment_id,
                        "payment_amount": str(payment.amount),
                        "total_refunded": str(total_refunded),
                        "refund_ids": [r.refund_id for r in sorted(r_list, key=lambda x: x.refund_id)],
                    },
                )
                exceptions.append(
                    build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.REFUND_EXCEEDS_PAYMENT,
                        severity=ExceptionSeverity.CRITICAL,
                        primary_entity=pay_ref,
                        related_entities=related_rfnd_refs,
                        rule_code=RULE_REFUND_LIMIT,
                        expected_value=str(payment.amount),
                        observed_value=str(total_refunded),
                        difference=diff,
                        evidence=evidence,
                    )
                )

        # 3. SettlementTransaction -> Entity Reference validation
        for stxn_id in sorted(self.index.stxns_by_id.keys()):
            for stxn in self.index.stxns_by_id[stxn_id]:
                stxn_ref = EntityReference(entity_type="settlement_transaction", entity_id=stxn.settlement_txn_id)

                # Check settlement exists
                settlement = self.index.get_settlement(stxn.settlement_id)
                if settlement is None:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_MISSING_FOREIGN_KEY,
                        rule_description=f"SettlementTransaction {stxn.settlement_txn_id} references missing settlement {stxn.settlement_id}.",
                        primary_entity=stxn_ref,
                        expected_value=stxn.settlement_id,
                        observed_value=None,
                        details={"settlement_txn_id": stxn.settlement_txn_id, "missing_settlement_id": stxn.settlement_id},
                    )
                    exceptions.append(
                        build_exception(
                            exception_id=exc_id,
                            exception_type=ReconciliationExceptionType.MISSING_RECORD,
                            severity=ExceptionSeverity.ERROR,
                            primary_entity=stxn_ref,
                            rule_code=RULE_MISSING_FOREIGN_KEY,
                            evidence=evidence,
                        )
                    )

                # Check referenced entity exists
                target_entity = None
                rule_link_code = ""
                if stxn.entity_type == SettlementTransactionEntityType.PAYMENT:
                    target_entity = self.index.get_payment(stxn.entity_id)
                    rule_link_code = RULE_PAYMENT_SETTLEMENT_LINK
                elif stxn.entity_type == SettlementTransactionEntityType.REFUND:
                    target_entity = self.index.get_refund(stxn.entity_id)
                    rule_link_code = RULE_REFUND_SETTLEMENT_LINK
                elif stxn.entity_type == SettlementTransactionEntityType.ADJUSTMENT:
                    target_entity = self.index.get_adjustment(stxn.entity_id)
                    rule_link_code = RULE_ADJUSTMENT_SETTLEMENT_LINK

                if target_entity is None:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_MISSING_FOREIGN_KEY,
                        rule_description=(
                            f"SettlementTransaction {stxn.settlement_txn_id} references missing {stxn.entity_type} "
                            f"'{stxn.entity_id}'."
                        ),
                        primary_entity=stxn_ref,
                        expected_value=stxn.entity_id,
                        observed_value=None,
                        details={
                            "settlement_txn_id": stxn.settlement_txn_id,
                            "entity_type": str(stxn.entity_type),
                            "missing_entity_id": stxn.entity_id,
                        },
                    )
                    exceptions.append(
                        build_exception(
                            exception_id=exc_id,
                            exception_type=ReconciliationExceptionType.MISSING_RECORD,
                            severity=ExceptionSeverity.ERROR,
                            primary_entity=stxn_ref,
                            rule_code=RULE_MISSING_FOREIGN_KEY,
                            evidence=evidence,
                        )
                    )
                else:
                    self.counter["match"] += 1
                    match_id = f"match_{self.counter['match']:04d}"
                    target_ref = EntityReference(entity_type=str(stxn.entity_type), entity_id=stxn.entity_id)
                    evidence = build_evidence(
                        rule_code=rule_link_code,
                        rule_description=f"SettlementTransaction {stxn.settlement_txn_id} successfully linked to {stxn.entity_type} {stxn.entity_id}.",
                        primary_entity=stxn_ref,
                        related_entities=[target_ref],
                        details={"settlement_txn_id": stxn.settlement_txn_id, "entity_type": str(stxn.entity_type), "entity_id": stxn.entity_id},
                    )
                    matches.append(
                        build_match(
                            match_id=match_id,
                            match_type=rule_link_code,
                            entities=[stxn_ref, target_ref],
                            evidence=evidence,
                        )
                    )

                    # Cross reference check on Payment settlement_id
                    if (
                        stxn.entity_type == SettlementTransactionEntityType.PAYMENT
                        and getattr(target_entity, "settlement_id", None) is not None
                        and target_entity.settlement_id != stxn.settlement_id
                    ):
                        self.counter["exc"] += 1
                        exc_id = f"exc_{self.counter['exc']:04d}"
                        evidence = build_evidence(
                            rule_code=RULE_CROSS_REFERENCE_MISMATCH,
                            rule_description=(
                                f"Payment {target_entity.payment_id} has settlement_id '{target_entity.settlement_id}' "
                                f"which disagrees with SettlementTransaction {stxn.settlement_txn_id} settlement_id '{stxn.settlement_id}'."
                            ),
                            primary_entity=target_ref,
                            related_entities=[stxn_ref],
                            expected_value=stxn.settlement_id,
                            observed_value=target_entity.settlement_id,
                            details={
                                "payment_id": target_entity.payment_id,
                                "payment_settlement_id": target_entity.settlement_id,
                                "stxn_settlement_id": stxn.settlement_id,
                            },
                        )
                        exceptions.append(
                            build_exception(
                                exception_id=exc_id,
                                exception_type=ReconciliationExceptionType.CROSS_REFERENCE_MISMATCH,
                                severity=ExceptionSeverity.WARNING,
                                primary_entity=target_ref,
                                related_entities=[stxn_ref],
                                rule_code=RULE_CROSS_REFERENCE_MISMATCH,
                                expected_value=stxn.settlement_id,
                                observed_value=target_entity.settlement_id,
                                evidence=evidence,
                            )
                        )

        return matches, exceptions

    def reconcile_settlements_to_bank(
        self,
    ) -> Tuple[
        Dict[str, Tuple[Optional[BankEntry], List[ReconciliationMatch], List[ReconciliationException]]],
        List[UnmatchedRecord],
    ]:
        """
        Reconciles each Settlement against external BankEntries using a deterministic multi-pass hierarchy.
        """
        results_by_settlement: Dict[
            str, Tuple[Optional[BankEntry], List[ReconciliationMatch], List[ReconciliationException]]
        ] = {}
        unmatched_records: List[UnmatchedRecord] = []

        matched_bank_entry_ids: Set[str] = set()
        matched_settlement_ids: Set[str] = set()

        sorted_settlements = sorted(self.index.observed.settlements, key=lambda s: s.settlement_id)
        sorted_bank_entries = sorted(self.index.observed.bank_entries, key=lambda b: b.bank_entry_id)

        # ---------------------------------------------------------------------
        # Pass 1: Exact UTR Match
        # ---------------------------------------------------------------------
        for settlement in sorted_settlements:
            results_by_settlement[settlement.settlement_id] = (None, [], [])
            if not settlement.utr:
                continue

            bank_candidates = self.index.get_bank_entries_for_utr(settlement.utr)
            if len(bank_candidates) == 1:
                bank_entry = bank_candidates[0]
                matched_bank_entry_ids.add(bank_entry.bank_entry_id)
                matched_settlement_ids.add(settlement.settlement_id)

                setl_ref = EntityReference(entity_type="settlement", entity_id=settlement.settlement_id)
                bank_ref = EntityReference(entity_type="bank_entry", entity_id=bank_entry.bank_entry_id)

                diff = bank_entry.amount - settlement.amount
                abs_diff = abs(diff)

                if abs_diff <= self.config.tolerance:
                    self.counter["match"] += 1
                    match_id = f"match_{self.counter['match']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_SETTLEMENT_BANK_EXACT,
                        rule_description="Settlement amount and UTR match BankEntry exactly.",
                        primary_entity=setl_ref,
                        related_entities=[bank_ref],
                        expected_value=str(settlement.amount),
                        observed_value=str(bank_entry.amount),
                        difference=diff,
                        details={
                            "settlement_id": settlement.settlement_id,
                            "bank_entry_id": bank_entry.bank_entry_id,
                            "utr": settlement.utr,
                            "settlement_amount": str(settlement.amount),
                            "bank_amount": str(bank_entry.amount),
                        },
                    )
                    match_obj = build_match(
                        match_id=match_id,
                        match_type=RULE_SETTLEMENT_BANK_EXACT,
                        entities=[setl_ref, bank_ref],
                        evidence=evidence,
                    )
                    results_by_settlement[settlement.settlement_id] = (bank_entry, [match_obj], [])
                else:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_SETTLEMENT_BANK_AMOUNT_MISMATCH,
                        rule_description=(
                            f"Settlement {settlement.settlement_id} amount ({settlement.amount}) differs from "
                            f"BankEntry {bank_entry.bank_entry_id} amount ({bank_entry.amount}) for matching UTR '{settlement.utr}'."
                        ),
                        primary_entity=setl_ref,
                        related_entities=[bank_ref],
                        expected_value=str(settlement.amount),
                        observed_value=str(bank_entry.amount),
                        difference=diff,
                        details={
                            "settlement_id": settlement.settlement_id,
                            "bank_entry_id": bank_entry.bank_entry_id,
                            "utr": settlement.utr,
                            "settlement_amount": str(settlement.amount),
                            "bank_amount": str(bank_entry.amount),
                            "difference": str(diff),
                        },
                    )
                    exc_obj = build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.BANK_AMOUNT_MISMATCH,
                        severity=ExceptionSeverity.CRITICAL,
                        primary_entity=setl_ref,
                        related_entities=[bank_ref],
                        rule_code=RULE_SETTLEMENT_BANK_AMOUNT_MISMATCH,
                        expected_value=str(settlement.amount),
                        observed_value=str(bank_entry.amount),
                        difference=diff,
                        evidence=evidence,
                    )
                    results_by_settlement[settlement.settlement_id] = (bank_entry, [], [exc_obj])

        # ---------------------------------------------------------------------
        # Pass 2: Identifier Mismatch (Unique Candidate Fallback)
        # ---------------------------------------------------------------------
        unmatched_settlements = [
            s for s in sorted_settlements if s.settlement_id not in matched_settlement_ids
        ]
        unmatched_bank_entries = [
            b for b in sorted_bank_entries if b.bank_entry_id not in matched_bank_entry_ids
        ]

        # Check for unique candidate pairing (same merchant, same amount, single orphan pair)
        for settlement in unmatched_settlements:
            setl_ref = EntityReference(entity_type="settlement", entity_id=settlement.settlement_id)
            candidate_bank_entries = [
                b
                for b in unmatched_bank_entries
                if b.merchant_id == settlement.merchant_id
                and abs(b.amount - settlement.amount) <= self.config.tolerance
                and b.bank_entry_id not in matched_bank_entry_ids
            ]

            if len(candidate_bank_entries) == 1:
                # Also verify settlement is the unique match for this bank entry
                candidate_bank = candidate_bank_entries[0]
                other_settlements = [
                    s
                    for s in unmatched_settlements
                    if s.merchant_id == candidate_bank.merchant_id
                    and abs(s.amount - candidate_bank.amount) <= self.config.tolerance
                ]

                if len(other_settlements) == 1:
                    matched_bank_entry_ids.add(candidate_bank.bank_entry_id)
                    matched_settlement_ids.add(settlement.settlement_id)
                    bank_ref = EntityReference(entity_type="bank_entry", entity_id=candidate_bank.bank_entry_id)

                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_SETTLEMENT_BANK_IDENTIFIER_MISMATCH,
                        rule_description=(
                            f"Settlement {settlement.settlement_id} (UTR: {settlement.utr}) and "
                            f"BankEntry {candidate_bank.bank_entry_id} (UTR: {candidate_bank.utr}) have identical "
                            f"amount ({settlement.amount}) and merchant ({settlement.merchant_id}) but differing UTRs."
                        ),
                        primary_entity=setl_ref,
                        related_entities=[bank_ref],
                        expected_value=settlement.utr,
                        observed_value=candidate_bank.utr,
                        details={
                            "settlement_id": settlement.settlement_id,
                            "settlement_utr": settlement.utr,
                            "bank_entry_id": candidate_bank.bank_entry_id,
                            "bank_utr": candidate_bank.utr,
                            "amount": str(settlement.amount),
                        },
                    )
                    exc_obj = build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.IDENTIFIER_MISMATCH,
                        severity=ExceptionSeverity.WARNING,
                        primary_entity=setl_ref,
                        related_entities=[bank_ref],
                        rule_code=RULE_SETTLEMENT_BANK_IDENTIFIER_MISMATCH,
                        expected_value=settlement.utr,
                        observed_value=candidate_bank.utr,
                        evidence=evidence,
                    )
                    results_by_settlement[settlement.settlement_id] = (candidate_bank, [], [exc_obj])

        # ---------------------------------------------------------------------
        # Pass 3: Missing Bank Entry for Processed Settlements
        # ---------------------------------------------------------------------
        for settlement in sorted_settlements:
            if settlement.settlement_id not in matched_settlement_ids:
                setl_ref = EntityReference(entity_type="settlement", entity_id=settlement.settlement_id)
                if settlement.status == SettlementStatus.PROCESSED and settlement.utr:
                    self.counter["exc"] += 1
                    exc_id = f"exc_{self.counter['exc']:04d}"
                    evidence = build_evidence(
                        rule_code=RULE_MISSING_BANK_ENTRY,
                        rule_description=(
                            f"Settlement {settlement.settlement_id} is marked PROCESSED with UTR '{settlement.utr}' "
                            f"but no corresponding BankEntry was found in ObservedWorld."
                        ),
                        primary_entity=setl_ref,
                        expected_value=settlement.utr,
                        observed_value=None,
                        details={"settlement_id": settlement.settlement_id, "utr": settlement.utr},
                    )
                    exc_obj = build_exception(
                        exception_id=exc_id,
                        exception_type=ReconciliationExceptionType.MISSING_RECORD,
                        severity=ExceptionSeverity.ERROR,
                        primary_entity=setl_ref,
                        rule_code=RULE_MISSING_BANK_ENTRY,
                        expected_value=settlement.utr,
                        observed_value=None,
                        evidence=evidence,
                    )
                    results_by_settlement[settlement.settlement_id] = (None, [], [exc_obj])

        # ---------------------------------------------------------------------
        # Pass 4: Collect Unmatched Bank Entries
        # ---------------------------------------------------------------------
        for bank_entry in sorted_bank_entries:
            if bank_entry.bank_entry_id not in matched_bank_entry_ids:
                bank_ref = EntityReference(entity_type="bank_entry", entity_id=bank_entry.bank_entry_id)
                unmatched_records.append(
                    build_unmatched(
                        entity=bank_ref,
                        reason=RULE_UNMATCHED_BANK_ENTRY,
                        details={
                            "bank_entry_id": bank_entry.bank_entry_id,
                            "amount": str(bank_entry.amount),
                            "utr": bank_entry.utr,
                            "account_number": bank_entry.account_number,
                            "merchant_id": bank_entry.merchant_id,
                        },
                    )
                )

        return results_by_settlement, unmatched_records
