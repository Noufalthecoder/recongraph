"""
Deterministic anomaly matching and evaluation against reconciliation findings.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.benchmark.metrics import compute_benchmark_metrics
from backend.app.benchmark.models import (
    AnomalyEvaluation,
    BenchmarkMetrics,
    DetectedIssue,
    ExpectedAnomaly,
)
from backend.app.reconciliation.models import ReconciliationResult
from simulator.observed.models import AnomalyManifest, AnomalyRecord, AnomalyType, ObservedWorld


# Normalized mapping from plural to singular entity types
ENTITY_NORM = {
    "merchant": "merchant",
    "merchants": "merchant",
    "order": "order",
    "orders": "order",
    "payment": "payment",
    "payments": "payment",
    "refund": "refund",
    "refunds": "refund",
    "adjustment": "adjustment",
    "adjustments": "adjustment",
    "settlement_transaction": "settlement_transaction",
    "settlement_transactions": "settlement_transaction",
    "stxn": "settlement_transaction",
    "stxns": "settlement_transaction",
    "settlement": "settlement",
    "settlements": "settlement",
    "bank_entry": "bank_entry",
    "bank_entries": "bank_entry",
    "bank": "bank_entry",
}

# Authoritative compatibility mapping between injected anomaly types and reconciliation exceptions
COMPATIBLE_EXCEPTIONS = {
    AnomalyType.AMOUNT_MISMATCH: {
        "AMOUNT_MISMATCH",
        "BANK_AMOUNT_MISMATCH",
        "SETTLEMENT_COMPOSITION_MISMATCH",
        "LINE_ITEM_ARITHMETIC_MISMATCH",
    },
    AnomalyType.MISSING_RECORD: {
        "MISSING_RECORD",
        "SETTLEMENT_COMPOSITION_MISMATCH",
        "INVALID_RELATIONSHIP",
        "UNMATCHED_RECORD",
    },
    AnomalyType.DUPLICATE_RECORD: {
        "DUPLICATE_RECORD",
        "DUPLICATE_UTR",
        "SETTLEMENT_COMPOSITION_MISMATCH",
    },
    AnomalyType.IDENTIFIER_MISMATCH: {
        "IDENTIFIER_MISMATCH",
        "CROSS_REFERENCE_MISMATCH",
        "UNMATCHED_RECORD",
        "MISSING_RECORD",
    },
}


def normalize_entity_type(etype: str) -> str:
    return ENTITY_NORM.get(etype.lower(), etype.lower())


def _enum_to_str(val: Any) -> str:
    if hasattr(val, "value"):
        return str(val.value)
    s = str(val)
    if "." in s:
        return s.split(".")[-1]
    return s


def is_compatible(anomaly_type: Any, exception_type: str) -> bool:
    a_key = _enum_to_str(anomaly_type)
    exc_key = _enum_to_str(exception_type)
    for k, compat_set in COMPATIBLE_EXCEPTIONS.items():
        if _enum_to_str(k) == a_key:
            return exc_key in compat_set or exception_type in compat_set
    return False


def extract_detected_issues(recon_result: ReconciliationResult) -> List[DetectedIssue]:
    """Extracts all detected exceptions and unmatched records into uniform DetectedIssue objects."""
    issues: List[DetectedIssue] = []

    # 1. Extract from exceptions
    for exc in recon_result.exceptions:
        settlement_id = exc.evidence.details.get("settlement_id")
        if not settlement_id and exc.primary_entity.entity_type == "settlement":
            settlement_id = exc.primary_entity.entity_id

        exc_type_str = _enum_to_str(exc.exception_type)
        severity_str = _enum_to_str(exc.severity)

        issues.append(
            DetectedIssue(
                issue_id=exc.exception_id,
                exception_type=exc_type_str,
                severity=severity_str,
                entity_type=exc.primary_entity.entity_type,
                entity_id=exc.primary_entity.entity_id,
                settlement_id=settlement_id,
                rule_code=exc.rule_code,
                difference=exc.difference,
                expected_value=exc.expected_value,
                observed_value=exc.observed_value,
                evidence=exc.evidence.details,
            )
        )

    # 2. Extract from unmatched records
    for idx, un in enumerate(recon_result.unmatched):
        un_id = f"unm_{idx + 1:04d}"
        issues.append(
            DetectedIssue(
                issue_id=un_id,
                exception_type="UNMATCHED_RECORD",
                severity="WARNING",
                entity_type=un.entity.entity_type,
                entity_id=un.entity.entity_id,
                settlement_id=un.details.get("settlement_id"),
                rule_code=un.reason,
                difference=None,
                expected_value=None,
                observed_value=None,
                evidence=un.details,
            )
        )

    issues.sort(key=lambda x: (x.exception_type, x.entity_type, x.entity_id, x.issue_id))
    return issues


def extract_expected_anomalies(manifest: AnomalyManifest) -> List[ExpectedAnomaly]:
    """Transforms AnomalyManifest records into immutable ExpectedAnomaly models."""
    expected: List[ExpectedAnomaly] = []
    for rec in manifest.records:
        expected.append(
            ExpectedAnomaly(
                anomaly_id=rec.anomaly_id,
                anomaly_type=rec.anomaly_type,
                target_entity_type=rec.target_entity_type,
                target_entity_id=rec.target_entity_id,
                target_field=rec.target_field,
                original_value=rec.original_value,
                observed_value=rec.observed_value,
                settlement_id=rec.settlement_id,
                description=rec.description,
            )
        )
    expected.sort(key=lambda x: (x.anomaly_type, x.target_entity_type, x.target_entity_id, x.anomaly_id))
    return expected


class AnomalyMatcher:
    """
    Evaluates detected issues against expected anomalies using a multi-pass hierarchy.
    """

    @classmethod
    def evaluate(
        cls,
        expected_anomalies: List[ExpectedAnomaly],
        detected_issues: List[DetectedIssue],
        total_records: int,
        total_settlements: int = 0,
        reconciled_settlements: int = 0,
        exception_settlements: int = 0,
    ) -> Tuple[List[AnomalyEvaluation], BenchmarkMetrics]:
        matched_anomaly_ids: Set[str] = set()
        matched_issue_ids: Set[str] = set()
        evaluations_by_anomaly_id: Dict[str, AnomalyEvaluation] = {}

        # ---------------------------------------------------------------------
        # PASS 1: Exact Target Entity & Compatible Exception Type
        # ---------------------------------------------------------------------
        for exp in expected_anomalies:
            if exp.anomaly_id in matched_anomaly_ids:
                continue

            candidates = [
                issue
                for issue in detected_issues
                if issue.issue_id not in matched_issue_ids
                and normalize_entity_type(issue.entity_type) == normalize_entity_type(exp.target_entity_type)
                and issue.entity_id == exp.target_entity_id
                and is_compatible(exp.anomaly_type, issue.exception_type)
            ]

            if len(candidates) == 1:
                cand = candidates[0]
                matched_anomaly_ids.add(exp.anomaly_id)
                matched_issue_ids.add(cand.issue_id)
                evaluations_by_anomaly_id[exp.anomaly_id] = AnomalyEvaluation(
                    anomaly_id=exp.anomaly_id,
                    expected_type=exp.anomaly_type,
                    detected_type=cand.exception_type,
                    matched=True,
                    match_pass="PASS_1_EXACT_ENTITY",
                    expected_entity=f"{normalize_entity_type(exp.target_entity_type)}:{exp.target_entity_id}",
                    detected_entity=f"{normalize_entity_type(cand.entity_type)}:{cand.entity_id}",
                    reason="Exact match on target entity type, entity ID, and compatible exception type.",
                    details={"issue_id": cand.issue_id, "rule_code": cand.rule_code},
                )

        # ---------------------------------------------------------------------
        # PASS 2: Settlement Context Match (for Composition / Batch anomalies)
        # ---------------------------------------------------------------------
        for exp in expected_anomalies:
            if exp.anomaly_id in matched_anomaly_ids or not exp.settlement_id:
                continue

            candidates = [
                issue
                for issue in detected_issues
                if issue.issue_id not in matched_issue_ids
                and (
                    issue.settlement_id == exp.settlement_id
                    or (issue.entity_type == "settlement" and issue.entity_id == exp.settlement_id)
                )
                and is_compatible(exp.anomaly_type, issue.exception_type)
            ]

            if len(candidates) == 1:
                cand = candidates[0]
                matched_anomaly_ids.add(exp.anomaly_id)
                matched_issue_ids.add(cand.issue_id)
                evaluations_by_anomaly_id[exp.anomaly_id] = AnomalyEvaluation(
                    anomaly_id=exp.anomaly_id,
                    expected_type=exp.anomaly_type,
                    detected_type=cand.exception_type,
                    matched=True,
                    match_pass="PASS_2_SETTLEMENT_CONTEXT",
                    expected_entity=f"{normalize_entity_type(exp.target_entity_type)}:{exp.target_entity_id}",
                    detected_entity=f"{normalize_entity_type(cand.entity_type)}:{cand.entity_id}",
                    reason="Matched on settlement context and compatible structural composition exception.",
                    details={"settlement_id": exp.settlement_id, "issue_id": cand.issue_id, "rule_code": cand.rule_code},
                )

        # ---------------------------------------------------------------------
        # PASS 3: Referenced Foreign Entity in Evidence Details
        # ---------------------------------------------------------------------
        for exp in expected_anomalies:
            if exp.anomaly_id in matched_anomaly_ids:
                continue

            candidates = [
                issue
                for issue in detected_issues
                if issue.issue_id not in matched_issue_ids
                and (
                    issue.evidence.get("missing_entity_id") == exp.target_entity_id
                    or issue.expected_value == exp.target_entity_id
                    or issue.evidence.get("payment_id") == exp.target_entity_id
                )
                and is_compatible(exp.anomaly_type, issue.exception_type)
            ]

            if len(candidates) == 1:
                cand = candidates[0]
                matched_anomaly_ids.add(exp.anomaly_id)
                matched_issue_ids.add(cand.issue_id)
                evaluations_by_anomaly_id[exp.anomaly_id] = AnomalyEvaluation(
                    anomaly_id=exp.anomaly_id,
                    expected_type=exp.anomaly_type,
                    detected_type=cand.exception_type,
                    matched=True,
                    match_pass="PASS_3_REFERENCED_FOREIGN_KEY",
                    expected_entity=f"{normalize_entity_type(exp.target_entity_type)}:{exp.target_entity_id}",
                    detected_entity=f"{normalize_entity_type(cand.entity_type)}:{cand.entity_id}",
                    reason="Matched referenced foreign key inside detected issue evidence details.",
                    details={"target_entity_id": exp.target_entity_id, "issue_id": cand.issue_id, "rule_code": cand.rule_code},
                )

        # ---------------------------------------------------------------------
        # PASS 4: Unique Orphan / Evidence Relationship Match
        # ---------------------------------------------------------------------
        for exp in expected_anomalies:
            if exp.anomaly_id in matched_anomaly_ids:
                continue

            candidates = [
                issue
                for issue in detected_issues
                if issue.issue_id not in matched_issue_ids
                and (
                    exp.target_entity_id in str(issue.evidence)
                    or (exp.observed_value and exp.observed_value in (issue.observed_value, issue.evidence.get("utr"), issue.evidence.get("bank_utr")))
                )
                and is_compatible(exp.anomaly_type, issue.exception_type)
            ]

            if len(candidates) == 1:
                cand = candidates[0]
                matched_anomaly_ids.add(exp.anomaly_id)
                matched_issue_ids.add(cand.issue_id)
                evaluations_by_anomaly_id[exp.anomaly_id] = AnomalyEvaluation(
                    anomaly_id=exp.anomaly_id,
                    expected_type=exp.anomaly_type,
                    detected_type=cand.exception_type,
                    matched=True,
                    match_pass="PASS_4_EVIDENCE_RELATIONSHIP",
                    expected_entity=f"{normalize_entity_type(exp.target_entity_type)}:{exp.target_entity_id}",
                    detected_entity=f"{normalize_entity_type(cand.entity_type)}:{cand.entity_id}",
                    reason="Matched unique candidate via evidence relationship and observed value.",
                    details={"observed_value": exp.observed_value, "issue_id": cand.issue_id, "rule_code": cand.rule_code},
                )

        # ---------------------------------------------------------------------
        # Collect Unmatched Expected Anomalies (False Negatives)
        # ---------------------------------------------------------------------
        for exp in expected_anomalies:
            if exp.anomaly_id not in matched_anomaly_ids:
                evaluations_by_anomaly_id[exp.anomaly_id] = AnomalyEvaluation(
                    anomaly_id=exp.anomaly_id,
                    expected_type=exp.anomaly_type,
                    detected_type=None,
                    matched=False,
                    match_pass=None,
                    expected_entity=f"{normalize_entity_type(exp.target_entity_type)}:{exp.target_entity_id}",
                    detected_entity=None,
                    reason="Expected anomaly was not detected by the reconciliation engine (False Negative).",
                    details={"description": exp.description},
                )

        evaluations = [evaluations_by_anomaly_id[exp.anomaly_id] for exp in expected_anomalies]
        evaluations.sort(key=lambda x: x.anomaly_id)

        # Metrics calculation
        tp = len(matched_anomaly_ids)
        fn = len(expected_anomalies) - tp
        fp = len(detected_issues) - len(matched_issue_ids)

        metrics = compute_benchmark_metrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            total_expected_anomalies=len(expected_anomalies),
            total_detected_issues=len(detected_issues),
            total_records=total_records,
            total_settlements=total_settlements,
            reconciled_settlements=reconciled_settlements,
            exception_settlements=exception_settlements,
        )

        return evaluations, metrics
