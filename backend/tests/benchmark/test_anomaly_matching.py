"""
Tests for deterministic AnomalyMatcher passes, compatibility, and ambiguity resolution.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark.matcher import AnomalyMatcher
from backend.app.benchmark.models import DetectedIssue, ExpectedAnomaly
from simulator.observed.models import AnomalyType


def test_pass_1_exact_entity_matching():
    """Verify Pass 1 matches when target entity type and entity ID match directly."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_0001",
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="bank_entry",
            target_entity_id="bank_001",
            target_field="amount",
            original_value="1000.00",
            observed_value="750.00",
            settlement_id="setl_001",
            description="Bank amount corrupted",
        )
    ]
    detected = [
        DetectedIssue(
            issue_id="exc_0001",
            exception_type="BANK_AMOUNT_MISMATCH",
            severity="CRITICAL",
            entity_type="bank_entry",
            entity_id="bank_001",
            settlement_id="setl_001",
            rule_code="SETTLEMENT_BANK_AMOUNT_MISMATCH",
            difference=Decimal("-250.00"),
            expected_value="1000.00",
            observed_value="750.00",
            evidence={},
        )
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 1
    assert evals[0].matched is True
    assert evals[0].match_pass == "PASS_1_EXACT_ENTITY"
    assert metrics.true_positives == 1
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0
    assert metrics.f1 == Decimal("1.0000")


def test_pass_2_settlement_composition_context_matching():
    """Verify Pass 2 matches settlement composition mismatch to missing STXN."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_0002",
            anomaly_type=AnomalyType.MISSING_RECORD,
            target_entity_type="settlement_transaction",
            target_entity_id="stxn_001",
            settlement_id="setl_001",
            description="STXN missing from batch",
        )
    ]
    detected = [
        DetectedIssue(
            issue_id="exc_0002",
            exception_type="SETTLEMENT_COMPOSITION_MISMATCH",
            severity="CRITICAL",
            entity_type="settlement",
            entity_id="setl_001",
            settlement_id="setl_001",
            rule_code="SETTLEMENT_COMPOSITION_SUM",
            difference=Decimal("-500.00"),
            expected_value="500.00",
            observed_value="1000.00",
            evidence={"settlement_id": "setl_001"},
        )
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 1
    assert evals[0].matched is True
    assert evals[0].match_pass == "PASS_2_SETTLEMENT_CONTEXT"
    assert metrics.true_positives == 1
    assert metrics.f1 == Decimal("1.0000")


def test_pass_3_referenced_foreign_key_matching():
    """Verify Pass 3 matches missing Payment referenced by SettlementTransaction."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_0003",
            anomaly_type=AnomalyType.MISSING_RECORD,
            target_entity_type="payment",
            target_entity_id="pay_999",
            description="Payment omitted from world",
        )
    ]
    detected = [
        DetectedIssue(
            issue_id="exc_0003",
            exception_type="MISSING_RECORD",
            severity="ERROR",
            entity_type="settlement_transaction",
            entity_id="stxn_001",
            rule_code="MISSING_FOREIGN_KEY",
            expected_value="pay_999",
            evidence={"missing_entity_id": "pay_999"},
        )
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 1
    assert evals[0].matched is True
    assert evals[0].match_pass == "PASS_3_REFERENCED_FOREIGN_KEY"
    assert metrics.true_positives == 1


def test_incompatible_exception_type_not_matched():
    """Verify incompatible exception type is not falsely matched."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_0004",
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="payment",
            target_entity_id="pay_001",
            description="Amount corrupted",
        )
    ]
    detected = [
        DetectedIssue(
            issue_id="exc_0004",
            exception_type="DUPLICATE_RECORD",  # Incompatible with AMOUNT_MISMATCH
            severity="ERROR",
            entity_type="payment",
            entity_id="pay_001",
            rule_code="DUPLICATE_PRIMARY_KEY",
            evidence={},
        )
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 1
    assert evals[0].matched is False
    assert metrics.true_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.f1 == Decimal("0.0000")


def test_ambiguous_multiple_candidates_not_guessed():
    """Verify when multiple detected issues compete for 1 expected anomaly without unique key, no false guess occurs."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_0005",
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="bank_entry",
            target_entity_id="bank_001",
            settlement_id="setl_001",
            description="Amount corrupted",
        )
    ]
    # Two identical candidate issues matching same settlement and entity
    detected = [
        DetectedIssue(
            issue_id="exc_0005A",
            exception_type="BANK_AMOUNT_MISMATCH",
            severity="CRITICAL",
            entity_type="bank_entry",
            entity_id="bank_001",
            settlement_id="setl_001",
            rule_code="SETTLEMENT_BANK_AMOUNT_MISMATCH",
            difference=Decimal("-250.00"),
            evidence={},
        ),
        DetectedIssue(
            issue_id="exc_0005B",
            exception_type="BANK_AMOUNT_MISMATCH",
            severity="CRITICAL",
            entity_type="bank_entry",
            entity_id="bank_001",
            settlement_id="setl_001",
            rule_code="SETTLEMENT_BANK_AMOUNT_MISMATCH",
            difference=Decimal("-100.00"),
            evidence={},
        ),
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    # Since len(candidates) == 2 in Pass 1, neither is guessed
    assert evals[0].matched is False
    assert metrics.true_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.false_positives == 2


def test_false_positive_detection_tracking():
    """Verify that spurious extra detections are correctly flagged as false positives."""
    expected = []  # Clean dataset, zero expected anomalies
    detected = [
        DetectedIssue(
            issue_id="exc_spurious_1",
            exception_type="AMOUNT_MISMATCH",
            severity="CRITICAL",
            entity_type="payment",
            entity_id="pay_001",
            rule_code="AMOUNT_MISMATCH",
            evidence={},
        )
    ]

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 0
    assert metrics.true_positives == 0
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0
    assert metrics.precision == Decimal("0.0000")
    assert metrics.recall == Decimal("0.0000")


def test_false_negative_detection_tracking():
    """Verify that un-detected anomalies are explicitly tracked as false negatives."""
    expected = [
        ExpectedAnomaly(
            anomaly_id="anom_missed",
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="bank_entry",
            target_entity_id="bank_999",
            description="Undetected corruption",
        )
    ]
    detected = []  # Engine detected nothing

    evals, metrics = AnomalyMatcher.evaluate(expected, detected, total_records=10)
    assert len(evals) == 1
    assert evals[0].matched is False
    assert evals[0].reason == "Expected anomaly was not detected by the reconciliation engine (False Negative)."
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.precision == Decimal("0.0000")
    assert metrics.recall == Decimal("0.0000")

