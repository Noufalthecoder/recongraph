"""
Unit and invariant tests for the deterministic reconciliation engine.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import sys
import pytest

from backend.app.models import (
    BankEntry,
    Currency,
    Merchant,
    MerchantStatus,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Refund,
    RefundStatus,
    Settlement,
    SettlementStatus,
    SettlementTransaction,
    SettlementTransactionEntityType,
    SettlementTransactionType,
)
from backend.app.reconciliation import (
    DeterministicReconciliationEngine,
    NormalizedObservationIndex,
    ReconciliationConfig,
    ReconciliationExceptionType,
)
from simulator.observed.models import ObservedWorld

UTC = timezone.utc
NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)


def make_minimal_valid_world():
    m = Merchant(merchant_id="merch_001", name="M1", status=MerchantStatus.ACTIVE, created_at=NOW)
    o = Order(order_id="order_001", merchant_id="merch_001", amount=Decimal("1000.00"), currency=Currency.INR, status=OrderStatus.PAID, created_at=NOW)
    p = Payment(payment_id="pay_001", order_id="order_001", merchant_id="merch_001", amount=Decimal("1000.00"), currency=Currency.INR, status=PaymentStatus.CAPTURED, method=PaymentMethod.UPI, created_at=NOW, captured_at=NOW, fee=Decimal("0.00"), tax=Decimal("0.00"), settlement_id="setl_001")
    stxn = SettlementTransaction(settlement_txn_id="stxn_001", settlement_id="setl_001", merchant_id="merch_001", entity_type=SettlementTransactionEntityType.PAYMENT, entity_id="pay_001", amount=Decimal("1000.00"), fee=Decimal("0.00"), tax=Decimal("0.00"), net_amount=Decimal("1000.00"), type=SettlementTransactionType.CREDIT, created_at=NOW)
    s = Settlement(settlement_id="setl_001", merchant_id="merch_001", amount=Decimal("1000.00"), currency=Currency.INR, status=SettlementStatus.PROCESSED, fees=Decimal("0.00"), tax=Decimal("0.00"), utr="MOCKUTR123", created_at=NOW, settled_at=NOW)
    b = BankEntry(bank_entry_id="bank_001", merchant_id="merch_001", account_number="ACCT1", amount=Decimal("1000.00"), currency=Currency.INR, utr="MOCKUTR123", transaction_date=NOW)

    return ObservedWorld(
        merchants=[m],
        orders=[o],
        payments=[p],
        refunds=[],
        adjustments=[],
        settlement_transactions=[stxn],
        settlements=[s],
        bank_entries=[b],
    )


def test_duplicate_primary_key_detected():
    """Verify duplicate primary key creates DUPLICATE_RECORD exception."""
    world = make_minimal_valid_world()
    dup_p = world.payments[0].model_copy()
    corrupted_world = world.model_copy(update={"payments": [world.payments[0], dup_p]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    dup_exc = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.DUPLICATE_RECORD]
    assert len(dup_exc) >= 1
    assert dup_exc[0].primary_entity.entity_id == "pay_001"


def test_missing_order_for_payment_detected():
    """Verify payment with non-existent order_id produces MISSING_RECORD exception."""
    world = make_minimal_valid_world()
    corrupted_world = world.model_copy(update={"orders": []})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    missing_exc = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.MISSING_RECORD]
    assert any(e.rule_code == "MISSING_FOREIGN_KEY" for e in missing_exc)


def test_refund_exceeds_payment_limit_detected():
    """Verify when sum(refunds) > payment.amount, REFUND_EXCEEDS_PAYMENT is flagged."""
    world = make_minimal_valid_world()
    r1 = Refund(
        refund_id="rfnd_001",
        payment_id="pay_001",
        merchant_id="merch_001",
        amount=Decimal("600.00"),
        currency=Currency.INR,
        status=RefundStatus.PROCESSED,
        created_at=NOW,
    )
    r2 = Refund(
        refund_id="rfnd_002",
        payment_id="pay_001",
        merchant_id="merch_001",
        amount=Decimal("500.00"),
        currency=Currency.INR,
        status=RefundStatus.PROCESSED,
        created_at=NOW,
    )
    corrupted_world = world.model_copy(update={"refunds": [r1, r2]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    limit_exc = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.REFUND_EXCEEDS_PAYMENT]
    assert len(limit_exc) == 1
    assert limit_exc[0].difference == Decimal("100.00")  # 1100 - 1000


def test_cross_reference_mismatch_detected():
    """Verify when Payment.settlement_id disagrees with STXN.settlement_id, CROSS_REFERENCE_MISMATCH is flagged."""
    world = make_minimal_valid_world()
    mismatched_p = world.payments[0].model_copy(update={"settlement_id": "setl_OTHER"})
    corrupted_world = world.model_copy(update={"payments": [mismatched_p]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    cross_exc = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.CROSS_REFERENCE_MISMATCH]
    assert len(cross_exc) == 1


def test_missing_bank_entry_for_processed_settlement():
    """Verify processed settlement without matching bank entry produces MISSING_RECORD."""
    world = make_minimal_valid_world()
    corrupted_world = world.model_copy(update={"bank_entries": []})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    missing_exc = [e for e in result.exceptions if e.rule_code == "MISSING_BANK_ENTRY"]
    assert len(missing_exc) == 1


def test_orphan_bank_entry_tracked_as_unmatched():
    """Verify extra bank entry is captured in unmatched records without crashing."""
    world = make_minimal_valid_world()
    orphan_bank = BankEntry(
        bank_entry_id="bank_999",
        merchant_id="merch_001",
        account_number="ACCT1",
        amount=Decimal("500.00"),
        currency=Currency.INR,
        utr="UNKNOWN_UTR",
        transaction_date=NOW,
    )
    expanded_world = world.model_copy(update={"bank_entries": [world.bank_entries[0], orphan_bank]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(expanded_world)

    unmatched_banks = [u for u in result.unmatched if u.entity.entity_id == "bank_999"]
    assert len(unmatched_banks) == 1
    assert unmatched_banks[0].reason == "UNMATCHED_BANK_ENTRY"


def test_line_item_arithmetic_mismatch_detected():
    """Verify STXN with incorrect net_amount produces LINE_ITEM_ARITHMETIC_MISMATCH."""
    world = make_minimal_valid_world()
    corrupted_stxn = world.settlement_transactions[0].model_copy(
        update={"amount": Decimal("1000.00"), "fee": Decimal("20.00"), "tax": Decimal("3.60"), "net_amount": Decimal("1000.00")}
    )
    corrupted_world = world.model_copy(update={"settlement_transactions": [corrupted_stxn]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    arith_exc = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.LINE_ITEM_ARITHMETIC_MISMATCH]
    assert len(arith_exc) == 1


def test_determinism_and_idempotency():
    """Verify running reconciliation repeatedly on the same ObservedWorld produces 100% identical results."""
    world = make_minimal_valid_world()
    engine = DeterministicReconciliationEngine()

    res1 = engine.reconcile(world)
    res2 = engine.reconcile(world)

    # Dumps match excluding run_id and processing_time_ms
    dump1 = res1.model_dump(exclude={"run_id": True, "metrics": {"processing_time_ms": True}})
    dump2 = res2.model_dump(exclude={"run_id": True, "metrics": {"processing_time_ms": True}})
    assert dump1 == dump2


def test_benchmark_isolation_no_ground_truth_imports():
    """Verify backend.app.reconciliation does not import GroundTruth or AnomalyManifest."""
    import backend.app.reconciliation.engine
    import backend.app.reconciliation.matcher
    import backend.app.reconciliation.composition
    import backend.app.reconciliation.indexer
    import backend.app.reconciliation.models
    import backend.app.reconciliation.rules
    import backend.app.reconciliation.exceptions

    recon_modules = [
        backend.app.reconciliation.engine,
        backend.app.reconciliation.matcher,
        backend.app.reconciliation.composition,
        backend.app.reconciliation.indexer,
        backend.app.reconciliation.models,
        backend.app.reconciliation.rules,
        backend.app.reconciliation.exceptions,
    ]

    for mod in recon_modules:
        mod_src = open(mod.__file__, "r", encoding="utf-8").read()
        assert "GroundTruth" not in mod_src
        assert "AnomalyManifest" not in mod_src
        assert "AnomalyRecord" not in mod_src
        assert "ScenarioLabel" not in mod_src
        assert "import random" not in mod_src


def test_duplicate_settlement_participation_detected():
    """Verify that referencing the same entity in multiple STXNs produces DUPLICATE_RECORD."""
    world = make_minimal_valid_world()
    extra_stxn = world.settlement_transactions[0].model_copy(
        update={"settlement_txn_id": "stxn_999"}
    )
    corrupted_world = world.model_copy(update={"settlement_transactions": [world.settlement_transactions[0], extra_stxn]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    dup_exc = [e for e in result.exceptions if e.rule_code == "DUPLICATE_SETTLEMENT_PARTICIPATION"]
    assert len(dup_exc) == 1
    assert dup_exc[0].primary_entity.entity_id == "pay_001"


def test_duplicate_utr_detected():
    """Verify that two BankEntries with the same UTR produces DUPLICATE_UTR."""
    world = make_minimal_valid_world()
    b2 = BankEntry(
        bank_entry_id="bank_002",
        merchant_id="merch_001",
        account_number="ACCT2",
        amount=Decimal("1000.00"),
        currency=Currency.INR,
        utr="MOCKUTR123",  # Same UTR as bank_001
        transaction_date=NOW,
    )
    corrupted_world = world.model_copy(update={"bank_entries": [world.bank_entries[0], b2]})

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(corrupted_world)

    assert result.status == "EXCEPTION"
    dup_utr = [e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.DUPLICATE_UTR]
    assert len(dup_utr) == 1
    assert dup_utr[0].observed_value == "MOCKUTR123"


def test_result_ordering_determinism():
    """Verify that settlements, matches, exceptions, and unmatched lists are sorted deterministically."""
    world = make_minimal_valid_world()
    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(world)

    # Settlements sorted by settlement_id
    settlement_ids = [s.settlement_id for s in result.settlements]
    assert settlement_ids == sorted(settlement_ids)

    # Matches sorted by (match_type, match_id)
    match_keys = [(m.match_type, m.match_id) for m in result.matches]
    assert match_keys == sorted(match_keys)

    # Exceptions sorted by (exception_type, primary_entity.entity_id, exception_id)
    exc_keys = [(e.exception_type, e.primary_entity.entity_id, e.exception_id) for e in result.exceptions]
    assert exc_keys == sorted(exc_keys)

    # Unmatched sorted by (entity.entity_type, entity.entity_id)
    unmatched_keys = [(u.entity.entity_type, u.entity.entity_id) for u in result.unmatched]
    assert unmatched_keys == sorted(unmatched_keys)


def test_decimal_float_rejection_in_config():
    """Verify float is rejected when passed to ReconciliationConfig."""
    with pytest.raises(ValueError, match="Float values are forbidden"):
        ReconciliationConfig(tolerance=0.01)  # type: ignore[arg-type]

