"""
Deterministic Reconciliation Engine orchestrator.
"""

import time
from decimal import Decimal
from typing import Dict, List, Optional

from backend.app.reconciliation.composition import SettlementCompositionValidator
from backend.app.reconciliation.indexer import NormalizedObservationIndex
from backend.app.reconciliation.matcher import DeterministicMatcher
from backend.app.reconciliation.models import (
    EntityReference,
    ReconciliationConfig,
    ReconciliationException,
    ReconciliationMatch,
    ReconciliationMetrics,
    ReconciliationResult,
    SettlementReconciliationResult,
    UnmatchedRecord,
)
from backend.app.reconciliation.rules import build_unmatched
from simulator.observed.models import ObservedWorld


class DeterministicReconciliationEngine:
    """
    Core rule-based deterministic reconciliation engine for ReconGraph.

    Consumes strictly an ObservedWorld and generates complete, auditable,
    reproducible reconciliation results and mathematical evidence.
    """

    def reconcile(
        self,
        observed: ObservedWorld,
        config: Optional[ReconciliationConfig] = None,
    ) -> ReconciliationResult:
        start_time = time.perf_counter()
        config = config or ReconciliationConfig()

        counter: Dict[str, int] = {"match": 0, "exc": 0}

        # 1. Ingestion and Indexing
        index = NormalizedObservationIndex(observed)
        matcher = DeterministicMatcher(index, config, counter)

        all_matches: List[ReconciliationMatch] = []
        all_exceptions: List[ReconciliationException] = []
        all_unmatched: List[UnmatchedRecord] = []

        # 2. Duplicate Detection
        dup_exceptions = matcher.detect_duplicates()
        all_exceptions.extend(dup_exceptions)

        # 3. Referential & Lifecycle Integrity
        ref_matches, ref_exceptions = matcher.validate_referential_integrity()
        all_matches.extend(ref_matches)
        all_exceptions.extend(ref_exceptions)

        # 4. Bank Matching Pass
        bank_reconciled_by_setl, unmatched_banks = matcher.reconcile_settlements_to_bank()
        all_unmatched.extend(unmatched_banks)

        # 5. Settlement Composition and Per-Settlement Results
        settlement_results: List[SettlementReconciliationResult] = []

        sorted_settlements = sorted(observed.settlements, key=lambda s: s.settlement_id)
        for settlement in sorted_settlements:
            stxns = index.get_stxns_for_settlement(settlement.settlement_id)

            calc_total, comp_matches, comp_exceptions = (
                SettlementCompositionValidator.validate_composition(
                    settlement, stxns, config, counter
                )
            )
            all_matches.extend(comp_matches)
            all_exceptions.extend(comp_exceptions)

            matched_bank_entry, bank_matches, bank_exceptions = bank_reconciled_by_setl.get(
                settlement.settlement_id, (None, [], [])
            )
            all_matches.extend(bank_matches)
            all_exceptions.extend(bank_exceptions)

            settlement_matches = comp_matches + bank_matches
            settlement_exceptions = comp_exceptions + bank_exceptions

            # Determine status of this settlement
            if settlement_exceptions:
                setl_status = "EXCEPTION"
            elif matched_bank_entry is not None and not comp_exceptions:
                setl_status = "RECONCILED"
            else:
                setl_status = "UNMATCHED"

            diff = settlement.amount - calc_total

            settlement_results.append(
                SettlementReconciliationResult(
                    settlement_id=settlement.settlement_id,
                    merchant_id=settlement.merchant_id,
                    status=setl_status,
                    settlement_amount=settlement.amount,
                    calculated_component_total=calc_total,
                    difference=diff,
                    bank_entry_id=matched_bank_entry.bank_entry_id if matched_bank_entry else None,
                    utr=settlement.utr,
                    line_item_count=len(stxns),
                    matches=settlement_matches,
                    exceptions=settlement_exceptions,
                )
            )

        # 6. Unsettled Payment Discovery
        for payment_id in sorted(index.payments_by_id.keys()):
            for payment in index.payments_by_id[payment_id]:
                stxns = index.stxns_by_target_entity.get(("payment", payment.payment_id), [])
                if not stxns and not payment.settlement_id:
                    pay_ref = EntityReference(entity_type="payment", entity_id=payment.payment_id)
                    all_unmatched.append(
                        build_unmatched(
                            entity=pay_ref,
                            reason="UNSETTLED_PAYMENT",
                            details={
                                "payment_id": payment.payment_id,
                                "amount": str(payment.amount),
                                "status": str(payment.status),
                            },
                        )
                    )

        # 7. Deterministic Sorting
        settlement_results.sort(key=lambda s: s.settlement_id)
        all_matches.sort(key=lambda m: (m.match_type, m.match_id))
        all_exceptions.sort(key=lambda e: (e.exception_type, e.primary_entity.entity_id, e.exception_id))
        all_unmatched.sort(key=lambda u: (u.entity.entity_type, u.entity.entity_id))

        # 8. Compute Metrics
        total_records = (
            len(observed.merchants)
            + len(observed.orders)
            + len(observed.payments)
            + len(observed.refunds)
            + len(observed.adjustments)
            + len(observed.settlement_transactions)
            + len(observed.settlements)
            + len(observed.bank_entries)
        )

        reconciled_settlements_count = sum(1 for s in settlement_results if s.status == "RECONCILED")
        exception_settlements_count = sum(1 for s in settlement_results if s.status == "EXCEPTION")
        unmatched_settlements_count = sum(1 for s in settlement_results if s.status == "UNMATCHED")
        unmatched_bank_entries_count = sum(1 for u in all_unmatched if u.entity.entity_type == "bank_entry")

        if observed.settlements:
            reconciliation_rate = (
                Decimal(reconciled_settlements_count) / Decimal(len(observed.settlements))
            ).quantize(Decimal("0.0001"))
        else:
            reconciliation_rate = Decimal("1.0000")

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 3)

        metrics = ReconciliationMetrics(
            total_records=total_records,
            total_merchants=len(observed.merchants),
            total_orders=len(observed.orders),
            total_payments=len(observed.payments),
            total_refunds=len(observed.refunds),
            total_adjustments=len(observed.adjustments),
            total_settlement_transactions=len(observed.settlement_transactions),
            total_settlements=len(observed.settlements),
            total_bank_entries=len(observed.bank_entries),
            reconciled_settlements_count=reconciled_settlements_count,
            exception_settlements_count=exception_settlements_count,
            unmatched_settlements_count=unmatched_settlements_count,
            unmatched_bank_entries_count=unmatched_bank_entries_count,
            total_matches_count=len(all_matches),
            total_exceptions_count=len(all_exceptions),
            total_unmatched_count=len(all_unmatched),
            settlement_reconciliation_rate=reconciliation_rate,
            processing_time_ms=processing_time_ms,
        )

        # 9. Top-Level Status Determination
        if not all_exceptions and (not settlement_results or reconciled_settlements_count == len(settlement_results)):
            overall_status = "RECONCILED"
        elif all_exceptions:
            overall_status = "EXCEPTION"
        elif unmatched_settlements_count > 0 or unmatched_bank_entries_count > 0:
            overall_status = "UNMATCHED"
        else:
            overall_status = "PARTIALLY_RECONCILED"

        summary = (
            f"Reconciliation {overall_status}: {reconciled_settlements_count}/{len(observed.settlements)} "
            f"settlements reconciled, {len(all_exceptions)} exceptions, {len(all_unmatched)} unmatched records."
        )

        run_id = f"recon_run_{int(start_time * 1000)}"

        return ReconciliationResult(
            run_id=run_id,
            status=overall_status,
            config=config,
            summary=summary,
            settlements=settlement_results,
            matches=all_matches,
            exceptions=all_exceptions,
            unmatched=all_unmatched,
            metrics=metrics,
        )
