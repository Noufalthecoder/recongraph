"""
Evidence attachment and reconciliation state integration for the FinancialGraph.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from backend.app.graph.models import GraphEvidence
from backend.app.reconciliation.models import ReconciliationResult


class GraphEvidenceLayer:
    """
    Binds deterministic reconciliation findings, matches, exceptions, and mathematical
    deltas directly to graph nodes.
    """

    def __init__(self, recon_result: Optional[ReconciliationResult] = None):
        self.recon_result = recon_result
        self.evidence_by_node_id: Dict[str, List[GraphEvidence]] = defaultdict(list)
        self.status_by_node_id: Dict[str, str] = {}
        self.exceptions_by_node_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        if recon_result:
            self._ingest_reconciliation_result(recon_result)

    def _ingest_reconciliation_result(self, result: ReconciliationResult) -> None:
        # 1. Ingest Per-Settlement Results
        for setl_res in result.settlements:
            setl_node_id = f"settlement:{setl_res.settlement_id}"
            self.status_by_node_id[setl_node_id] = setl_res.status

            if setl_res.bank_entry_id:
                bank_node_id = f"bank_entry:{setl_res.bank_entry_id}"
                self.status_by_node_id[bank_node_id] = setl_res.status

            for m in setl_res.matches:
                related_ids = [f"{e.entity_type}:{e.entity_id}" for e in m.entities]
                ev = GraphEvidence(
                    status="RECONCILED",
                    rule_code=m.evidence.rule_code,
                    severity="INFO",
                    explanation=m.evidence.rule_description,
                    expected_value=m.evidence.expected_value,
                    observed_value=m.evidence.observed_value,
                    difference=m.evidence.difference,
                    related_node_ids=related_ids,
                    details=m.evidence.details,
                )
                self.evidence_by_node_id[setl_node_id].append(ev)

            for exc in setl_res.exceptions:
                related_ids = [f"{e.entity_type}:{e.entity_id}" for e in exc.related_entities]
                ev = GraphEvidence(
                    status="EXCEPTION",
                    rule_code=exc.rule_code,
                    severity=str(exc.severity),
                    explanation=exc.evidence.rule_description,
                    expected_value=exc.expected_value,
                    observed_value=exc.observed_value,
                    difference=exc.difference,
                    related_node_ids=related_ids,
                    details=exc.evidence.details,
                )
                self.evidence_by_node_id[setl_node_id].append(ev)

        # 2. Ingest Top-Level Exceptions
        for exc in result.exceptions:
            primary_node_id = f"{exc.primary_entity.entity_type}:{exc.primary_entity.entity_id}"
            self.status_by_node_id[primary_node_id] = "EXCEPTION"

            related_ids = [f"{e.entity_type}:{e.entity_id}" for e in exc.related_entities]
            ev = GraphEvidence(
                status="EXCEPTION",
                rule_code=exc.rule_code,
                severity=str(exc.severity),
                explanation=exc.evidence.rule_description,
                expected_value=exc.expected_value,
                observed_value=exc.observed_value,
                difference=exc.difference,
                related_node_ids=related_ids,
                details=exc.evidence.details,
            )
            self.evidence_by_node_id[primary_node_id].append(ev)

            exc_dict = {
                "exception_id": exc.exception_id,
                "exception_type": str(exc.exception_type),
                "severity": str(exc.severity),
                "rule_code": exc.rule_code,
                "primary_entity": f"{exc.primary_entity.entity_type}:{exc.primary_entity.entity_id}",
                "expected_value": exc.expected_value,
                "observed_value": exc.observed_value,
                "difference": str(exc.difference) if exc.difference is not None else None,
                "details": exc.evidence.details,
            }
            self.exceptions_by_node_id[primary_node_id].append(exc_dict)

            # Also attach to settlement if present in details
            setl_id = exc.evidence.details.get("settlement_id")
            if setl_id:
                s_node = f"settlement:{setl_id}"
                self.status_by_node_id[s_node] = "EXCEPTION"
                self.exceptions_by_node_id[s_node].append(exc_dict)

        # 3. Ingest Unmatched Records
        for un in result.unmatched:
            node_id = f"{un.entity.entity_type}:{un.entity.entity_id}"
            self.status_by_node_id[node_id] = "UNMATCHED"
            ev = GraphEvidence(
                status="UNMATCHED",
                rule_code=un.reason,
                severity="WARNING",
                explanation=f"Unmatched record: {un.reason}",
                expected_value=None,
                observed_value=None,
                difference=None,
                related_node_ids=[],
                details=un.details,
            )
            self.evidence_by_node_id[node_id].append(ev)

    def get_node_evidence(self, node_id: str) -> List[GraphEvidence]:
        return self.evidence_by_node_id.get(node_id, [])

    def get_node_status(self, node_id: str) -> str:
        return self.status_by_node_id.get(node_id, "CLEAN")

    def get_node_exceptions(self, node_id: str) -> List[Dict[str, Any]]:
        return self.exceptions_by_node_id.get(node_id, [])
