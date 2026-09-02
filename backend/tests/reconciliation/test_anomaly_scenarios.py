"""
Tests for Core Deterministic Reconciliation on Anomaly-Injected Observed Worlds.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.reconciliation import (
    DeterministicReconciliationEngine,
    ReconciliationConfig,
    ReconciliationExceptionType,
)
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
)


def get_gt(scenario_type: str, seed: int = 42):
    sim_config = SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type=scenario_type,
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP",
    )
    return Simulator(sim_config).run()


def test_bank_amount_mismatch_detected_with_evidence():
    """
    Verifies that when a BankEntry amount is altered by -₹250, the engine detects
    BANK_AMOUNT_MISMATCH with exact mathematical evidence without knowing anomaly metadata.
    """
    gt = get_gt("adjustment_v1")
    delta = Decimal("-250.00")
    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=delta,
                target_index=0,
            )
        ],
    )
    obs_world, _ = ObservationGenerator.generate(gt, config)

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs_world)

    assert result.status == "EXCEPTION"
    assert len(result.exceptions) >= 1

    bank_exceptions = [
        e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.BANK_AMOUNT_MISMATCH
    ]
    assert len(bank_exceptions) == 1
    exc = bank_exceptions[0]

    assert exc.primary_entity.entity_type == "settlement"
    assert exc.difference == delta
    assert exc.expected_value == "14396.00"
    assert exc.observed_value == "14146.00"
    assert exc.evidence.details["difference"] == str(delta)


def test_missing_settlement_transaction_detected_as_composition_mismatch():
    """
    Verifies that when a SettlementTransaction is missing from ObservedWorld,
    the engine flags SETTLEMENT_COMPOSITION_MISMATCH with the exact delta.
    """
    gt = get_gt("adjustment_v1")
    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.MISSING_RECORD,
                target_entity_type="settlement_transaction",
                target_index=0,
            )
        ],
    )
    obs_world, _ = ObservationGenerator.generate(gt, config)

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs_world)

    assert result.status == "EXCEPTION"
    comp_exceptions = [
        e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.SETTLEMENT_COMPOSITION_MISMATCH
    ]
    assert len(comp_exceptions) == 1
    exc = comp_exceptions[0]
    assert exc.primary_entity.entity_type == "settlement"
    assert exc.difference != Decimal("0.00")


def test_missing_payment_record_detected_as_referential_integrity_violation():
    """
    Verifies that when a Payment is missing from ObservedWorld, the engine detects
    MISSING_RECORD when evaluating the SettlementTransaction referencing it.
    """
    gt = get_gt("many_to_one_v1")
    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.MISSING_RECORD,
                target_entity_type="payment",
                target_index=0,
            )
        ],
    )
    obs_world, _ = ObservationGenerator.generate(gt, config)

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs_world)

    assert result.status == "EXCEPTION"
    missing_exceptions = [
        e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.MISSING_RECORD
    ]
    assert len(missing_exceptions) >= 1
    assert any(e.rule_code == "MISSING_FOREIGN_KEY" for e in missing_exceptions)


def test_duplicate_settlement_transaction_detected_as_duplicate_record():
    """
    Verifies that duplicate SettlementTransactions are flagged as DUPLICATE_RECORD.
    """
    gt = get_gt("minimal_lifecycle_v1")
    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="settlement_transaction",
                target_index=0,
            )
        ],
    )
    obs_world, _ = ObservationGenerator.generate(gt, config)

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs_world)

    assert result.status == "EXCEPTION"
    dup_exceptions = [
        e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.DUPLICATE_RECORD
    ]
    assert len(dup_exceptions) >= 1


def test_identifier_mismatch_detected_on_mutated_utr_candidate_pair():
    """
    Verifies that when a single BankEntry UTR is mutated with matching amount,
    the engine flags IDENTIFIER_MISMATCH and exposes candidate relationship evidence.
    """
    gt = get_gt("minimal_lifecycle_v1")
    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                target_entity_type="bank_entry",
                target_field="utr",
                target_index=0,
            )
        ],
    )
    obs_world, _ = ObservationGenerator.generate(gt, config)

    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs_world)

    assert result.status == "EXCEPTION"
    id_exceptions = [
        e for e in result.exceptions if e.exception_type == ReconciliationExceptionType.IDENTIFIER_MISMATCH
    ]
    assert len(id_exceptions) == 1
    exc = id_exceptions[0]
    assert exc.primary_entity.entity_type == "settlement"
    assert exc.observed_value.endswith("_MISMATCH")
