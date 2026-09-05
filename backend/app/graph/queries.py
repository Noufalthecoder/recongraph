"""
High-level investigation queries for traversing causal financial neighborhoods and evidence.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Union

from backend.app.graph.evidence import GraphEvidenceLayer
from backend.app.graph.index import GraphIndex
from backend.app.graph.models import (
    FinancialGraph,
    GraphEdge,
    GraphNode,
    InvestigationResult,
    InvestigationTarget,
)
from backend.app.graph.traversal import get_subgraph
from backend.app.reconciliation.models import ReconciliationException


class InvestigationQueryEngine:
    """
    Executes deterministic investigation queries over the FinancialGraph and GraphEvidenceLayer.
    """

    def __init__(self, graph: FinancialGraph, evidence_layer: Optional[GraphEvidenceLayer] = None):
        self.graph = graph
        self.index = GraphIndex(graph)
        self.evidence_layer = evidence_layer or GraphEvidenceLayer()

    def get_settlement_investigation(self, settlement_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="settlement", entity_id=settlement_id)
        setl_node_id = f"settlement:{settlement_id}"
        target_node = self.index.get_node(setl_node_id)

        if not target_node:
            return InvestigationResult(
                target=target,
                target_node=None,
                connected_nodes=[],
                connected_edges=[],
                reconciliation_status="UNMATCHED",
                evidence=[],
                exceptions=[],
                summary_facts={"error": f"Settlement {settlement_id} not found in graph"},
            )

        # Collect Causal Neighborhood Subgraph
        nodes, edges = get_subgraph(self.index, setl_node_id, max_depth=4)

        # Categorize constituent nodes
        payments: List[GraphNode] = []
        refunds: List[GraphNode] = []
        adjustments: List[GraphNode] = []
        transfers: List[GraphNode] = []
        stxns: List[GraphNode] = []
        bank_entries: List[GraphNode] = []

        for node in nodes:
            if node.entity_type == "payment":
                payments.append(node)
            elif node.entity_type == "refund":
                refunds.append(node)
            elif node.entity_type == "adjustment":
                adjustments.append(node)
            elif node.entity_type == "transfer":
                transfers.append(node)
            elif node.entity_type == "settlement_transaction":
                stxns.append(node)
            elif node.entity_type == "bank_entry":
                bank_entries.append(node)

        # Mathematical breakdown from STXNs and Settlement
        payments_net = sum(
            (Decimal(st.attributes["net_amount"]) for st in stxns if st.attributes.get("entity_type") == "payment"),
            Decimal("0.00"),
        )
        refunds_net = sum(
            (Decimal(st.attributes["net_amount"]) for st in stxns if st.attributes.get("entity_type") == "refund"),
            Decimal("0.00"),
        )
        adjustments_net = sum(
            (Decimal(st.attributes["net_amount"]) for st in stxns if st.attributes.get("entity_type") == "adjustment"),
            Decimal("0.00"),
        )
        transfers_net = sum(
            (Decimal(st.attributes["net_amount"]) for st in stxns if st.attributes.get("entity_type") == "transfer"),
            Decimal("0.00"),
        )

        calculated_total = payments_net + refunds_net + adjustments_net + transfers_net
        setl_amount = Decimal(target_node.attributes.get("amount", "0.00"))
        settlement_delta = calculated_total - setl_amount

        bank_amount = Decimal(bank_entries[0].attributes.get("amount", "0.00")) if bank_entries else None
        bank_delta = (bank_amount - setl_amount) if bank_amount is not None else None

        status = self.evidence_layer.get_node_status(setl_node_id)
        evidence = self.evidence_layer.get_node_evidence(setl_node_id)
        exceptions = self.evidence_layer.get_node_exceptions(setl_node_id)

        summary_facts = {
            "settlement_id": settlement_id,
            "merchant_id": target_node.attributes.get("merchant_id"),
            "settlement_amount": str(setl_amount),
            "currency": target_node.attributes.get("currency", "INR"),
            "utr": target_node.attributes.get("utr"),
            "status": target_node.attributes.get("status"),
            "constituent_transactions_count": len(stxns),
            "payments_count": len(payments),
            "refunds_count": len(refunds),
            "adjustments_count": len(adjustments),
            "transfers_count": len(transfers),
            "bank_entry_id": bank_entries[0].entity_id if bank_entries else None,
            "bank_amount": str(bank_amount) if bank_amount is not None else None,
            "constituent_payments": [
                {
                    "entity_id": p.entity_id,
                    "amount": str(p.attributes.get("amount", "0.00")),
                    "fee": str(p.attributes.get("fee", "0.00")),
                    "tax": str(p.attributes.get("tax", "0.00")),
                    "status": p.attributes.get("status"),
                }
                for p in payments
            ],
            "constituent_refunds": [
                {
                    "entity_id": r.entity_id,
                    "amount": str(r.attributes.get("amount", "0.00")),
                    "status": r.attributes.get("status"),
                }
                for r in refunds
            ],
            "constituent_adjustments": [
                {
                    "entity_id": a.entity_id,
                    "amount": str(a.attributes.get("amount", "0.00")),
                    "reason": a.attributes.get("reason"),
                }
                for a in adjustments
            ],
            "mathematical_breakdown": {
                "payments_net_total": str(payments_net),
                "refunds_net_total": str(refunds_net),
                "adjustments_net_total": str(adjustments_net),
                "transfers_net_total": str(transfers_net),
                "calculated_component_total": str(calculated_total),
                "settlement_amount": str(setl_amount),
                "composition_delta": str(settlement_delta),
                "bank_amount": str(bank_amount) if bank_amount is not None else None,
                "bank_delta": str(bank_delta) if bank_delta is not None else None,
            },
        }

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=status,
            evidence=evidence,
            exceptions=exceptions,
            summary_facts=summary_facts,
        )

    def get_payment_investigation(self, payment_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="payment", entity_id=payment_id)
        pay_node_id = f"payment:{payment_id}"
        target_node = self.index.get_node(pay_node_id)

        if not target_node:
            return InvestigationResult(
                target=target,
                target_node=None,
                connected_nodes=[],
                connected_edges=[],
                reconciliation_status="UNMATCHED",
                evidence=[],
                exceptions=[],
                summary_facts={"error": f"Payment {payment_id} not found in graph"},
            )

        nodes, edges = get_subgraph(self.index, pay_node_id, max_depth=3)
        status = self.evidence_layer.get_node_status(pay_node_id)
        evidence = self.evidence_layer.get_node_evidence(pay_node_id)
        exceptions = self.evidence_layer.get_node_exceptions(pay_node_id)

        pay_amt = Decimal(target_node.attributes.get("amount", "0.00"))
        fee_amt = Decimal(target_node.attributes.get("fee", "0.00"))
        tax_amt = Decimal(target_node.attributes.get("tax", "0.00"))
        net_amt = pay_amt - fee_amt - tax_amt

        # Find linked settlement and bank entry
        setl_id = target_node.attributes.get("settlement_id")
        bank_utr = None
        bank_entry_id = None
        for n in nodes:
            if n.entity_type == "settlement" and not setl_id:
                setl_id = n.entity_id
            elif n.entity_type == "bank_entry":
                bank_entry_id = n.entity_id
                bank_utr = n.attributes.get("utr")

        summary_facts = {
            "payment_id": payment_id,
            "order_id": target_node.attributes.get("order_id"),
            "merchant_id": target_node.attributes.get("merchant_id"),
            "amount": str(pay_amt),
            "fee": str(fee_amt),
            "tax": str(tax_amt),
            "net_amount": str(net_amt),
            "settlement_id": setl_id,
            "bank_entry_id": bank_entry_id,
            "utr": bank_utr or target_node.attributes.get("utr"),
            "status": target_node.attributes.get("status"),
        }

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=status,
            evidence=evidence,
            exceptions=exceptions,
            summary_facts=summary_facts,
        )

    def get_order_investigation(self, order_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="order", entity_id=order_id)
        node_id = f"order:{order_id}"
        target_node = self.index.get_node(node_id)
        nodes, edges = get_subgraph(self.index, node_id, max_depth=3) if target_node else ([], [])

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=self.evidence_layer.get_node_status(node_id),
            evidence=self.evidence_layer.get_node_evidence(node_id),
            exceptions=self.evidence_layer.get_node_exceptions(node_id),
            summary_facts={"order_id": order_id, "amount": target_node.attributes.get("amount") if target_node else None},
        )

    def get_refund_investigation(self, refund_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="refund", entity_id=refund_id)
        node_id = f"refund:{refund_id}"
        target_node = self.index.get_node(node_id)
        nodes, edges = get_subgraph(self.index, node_id, max_depth=3) if target_node else ([], [])

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=self.evidence_layer.get_node_status(node_id),
            evidence=self.evidence_layer.get_node_evidence(node_id),
            exceptions=self.evidence_layer.get_node_exceptions(node_id),
            summary_facts={
                "refund_id": refund_id,
                "payment_id": target_node.attributes.get("payment_id") if target_node else None,
                "amount": target_node.attributes.get("amount") if target_node else None,
            },
        )

    def get_adjustment_investigation(self, adjustment_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="adjustment", entity_id=adjustment_id)
        node_id = f"adjustment:{adjustment_id}"
        target_node = self.index.get_node(node_id)
        nodes, edges = get_subgraph(self.index, node_id, max_depth=3) if target_node else ([], [])

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=self.evidence_layer.get_node_status(node_id),
            evidence=self.evidence_layer.get_node_evidence(node_id),
            exceptions=self.evidence_layer.get_node_exceptions(node_id),
            summary_facts={
                "adjustment_id": adjustment_id,
                "amount": target_node.attributes.get("amount") if target_node else None,
                "reason": target_node.attributes.get("reason") if target_node else None,
            },
        )

    def get_bank_entry_investigation(self, bank_entry_id: str) -> InvestigationResult:
        target = InvestigationTarget(entity_type="bank_entry", entity_id=bank_entry_id)
        node_id = f"bank_entry:{bank_entry_id}"
        target_node = self.index.get_node(node_id)
        nodes, edges = get_subgraph(self.index, node_id, max_depth=3) if target_node else ([], [])

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=self.evidence_layer.get_node_status(node_id),
            evidence=self.evidence_layer.get_node_evidence(node_id),
            exceptions=self.evidence_layer.get_node_exceptions(node_id),
            summary_facts={
                "bank_entry_id": bank_entry_id,
                "amount": target_node.attributes.get("amount") if target_node else None,
                "utr": target_node.attributes.get("utr") if target_node else None,
            },
        )

    def get_exception_neighborhood(
        self, exception: Union[ReconciliationException, Dict[str, Any]]
    ) -> InvestigationResult:
        """
        Given a reconciliation exception, locates the primary entity and its causal neighborhood.
        """
        if isinstance(exception, ReconciliationException):
            primary_etype = exception.primary_entity.entity_type
            primary_eid = exception.primary_entity.entity_id
            rule_code = exception.rule_code
            details = exception.evidence.details
        else:
            primary_parts = exception.get("primary_entity", ":").split(":")
            primary_etype = primary_parts[0] if len(primary_parts) > 1 else "settlement"
            primary_eid = primary_parts[1] if len(primary_parts) > 1 else primary_parts[0]
            rule_code = exception.get("rule_code", "UNKNOWN_EXCEPTION")
            details = exception.get("details", {})

        target = InvestigationTarget(entity_type=primary_etype, entity_id=primary_eid)
        primary_node_id = f"{primary_etype}:{primary_eid}"
        target_node = self.index.get_node(primary_node_id)

        # If primary node isn't in graph (e.g. missing entity), try finding neighborhood from settlement_id
        if not target_node and "settlement_id" in details:
            setl_id = details["settlement_id"]
            return self.get_settlement_investigation(setl_id)

        if not target_node:
            return InvestigationResult(
                target=target,
                target_node=None,
                connected_nodes=[],
                connected_edges=[],
                reconciliation_status="EXCEPTION",
                evidence=[],
                exceptions=[{"rule_code": rule_code, "details": details}],
                summary_facts={"error": f"Primary entity {primary_node_id} not found in graph"},
            )

        nodes, edges = get_subgraph(self.index, primary_node_id, max_depth=3)
        status = self.evidence_layer.get_node_status(primary_node_id)
        evidence = self.evidence_layer.get_node_evidence(primary_node_id)
        exceptions = self.evidence_layer.get_node_exceptions(primary_node_id)

        return InvestigationResult(
            target=target,
            target_node=target_node,
            connected_nodes=nodes,
            connected_edges=edges,
            reconciliation_status=status or "EXCEPTION",
            evidence=evidence,
            exceptions=exceptions or [{"rule_code": rule_code, "details": details}],
            summary_facts={
                "exception_rule": rule_code,
                "primary_entity": primary_node_id,
                "details": details,
            },
        )
