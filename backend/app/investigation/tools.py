"""
Read-only investigation tools exposing graph traversals, reconciliation evidence, and entity lookups.
"""

from typing import Any, Dict, List, Optional

from backend.app.graph.evidence import GraphEvidenceLayer
from backend.app.graph.index import GraphIndex
from backend.app.graph.models import FinancialGraph
from backend.app.graph.queries import InvestigationQueryEngine
from backend.app.graph.traversal import find_path, get_neighbors
from backend.app.investigation.models import InvestigationToolResult
from backend.app.reconciliation.models import ReconciliationResult


class InvestigationToolRegistry:
    """
    Provides secure, read-only tools for querying the FinancialGraph, GraphEvidenceLayer,
    and InvestigationQueryEngine.
    """

    def __init__(
        self,
        graph: FinancialGraph,
        evidence_layer: Optional[GraphEvidenceLayer] = None,
        recon_result: Optional[ReconciliationResult] = None,
    ):
        self.graph = graph
        self.evidence_layer = evidence_layer or GraphEvidenceLayer(recon_result)
        self.query_engine = InvestigationQueryEngine(graph, self.evidence_layer)
        self.index = GraphIndex(graph)
        self.recon_result = recon_result

    def search_financial_entities(self, query: str) -> InvestigationToolResult:
        """Searches known entities by ID or partial token in the graph index."""
        q = query.strip().lower()
        candidates: List[Dict[str, Any]] = []

        for node in self.graph.nodes:
            if (
                q in node.node_id.lower()
                or q in node.entity_id.lower()
                or q in node.display_label.lower()
                or (node.attributes.get("utr") and q in node.attributes["utr"].lower())
            ):
                candidates.append({
                    "node_id": node.node_id,
                    "entity_type": node.entity_type,
                    "entity_id": node.entity_id,
                    "display_label": node.display_label,
                    "status": self.evidence_layer.get_node_status(node.node_id),
                })

        return InvestigationToolResult(
            tool_name="search_financial_entities",
            success=True,
            structured_data={"query": query, "candidates_count": len(candidates), "candidates": candidates},
            evidence_refs=[c["node_id"] for c in candidates],
        )

    def get_settlement_investigation(self, settlement_id: str) -> InvestigationToolResult:
        """Retrieves complete settlement investigation, mathematical breakdown, and evidence."""
        inv = self.query_engine.get_settlement_investigation(settlement_id)
        if inv.target_node is None:
            return InvestigationToolResult(
                tool_name="get_settlement_investigation",
                success=False,
                structured_data={},
                error=f"Settlement '{settlement_id}' was not found in the observed graph.",
            )

        data = {
            "settlement_id": settlement_id,
            "status": inv.reconciliation_status,
            "summary_facts": inv.summary_facts,
            "exceptions": inv.exceptions,
            "evidence": [e.model_dump() for e in inv.evidence],
            "connected_nodes": [n.node_id for n in inv.connected_nodes],
            "connected_edges": [e.edge_id for e in inv.connected_edges],
        }
        refs = [f"settlement:{settlement_id}"] + [n.node_id for n in inv.connected_nodes if n.entity_type in ("bank_entry", "settlement_transaction")]

        return InvestigationToolResult(
            tool_name="get_settlement_investigation",
            success=True,
            structured_data=data,
            evidence_refs=refs,
        )

    def get_payment_investigation(self, payment_id: str) -> InvestigationToolResult:
        """Retrieves payment context including order, refunds, STXNs, and settlement status."""
        inv = self.query_engine.get_payment_investigation(payment_id)
        if inv.target_node is None:
            return InvestigationToolResult(
                tool_name="get_payment_investigation",
                success=False,
                structured_data={},
                error=f"Payment '{payment_id}' was not found in the observed graph.",
            )

        data = {
            "payment_id": payment_id,
            "status": inv.reconciliation_status,
            "summary_facts": inv.summary_facts,
            "exceptions": inv.exceptions,
            "evidence": [e.model_dump() for e in inv.evidence],
            "connected_nodes": [n.node_id for n in inv.connected_nodes],
        }
        return InvestigationToolResult(
            tool_name="get_payment_investigation",
            success=True,
            structured_data=data,
            evidence_refs=[f"payment:{payment_id}"],
        )

    def get_order_investigation(self, order_id: str) -> InvestigationToolResult:
        """Retrieves order context and connected payments."""
        inv = self.query_engine.get_order_investigation(order_id)
        return InvestigationToolResult(
            tool_name="get_order_investigation",
            success=inv.target_node is not None,
            structured_data={
                "order_id": order_id,
                "summary_facts": inv.summary_facts,
                "connected_nodes": [n.node_id for n in inv.connected_nodes],
            },
            evidence_refs=[f"order:{order_id}"] if inv.target_node else [],
            error=None if inv.target_node else f"Order '{order_id}' not found.",
        )

    def get_refund_investigation(self, refund_id: str) -> InvestigationToolResult:
        """Retrieves refund context and parent payment."""
        inv = self.query_engine.get_refund_investigation(refund_id)
        return InvestigationToolResult(
            tool_name="get_refund_investigation",
            success=inv.target_node is not None,
            structured_data={
                "refund_id": refund_id,
                "summary_facts": inv.summary_facts,
                "connected_nodes": [n.node_id for n in inv.connected_nodes],
            },
            evidence_refs=[f"refund:{refund_id}"] if inv.target_node else [],
            error=None if inv.target_node else f"Refund '{refund_id}' not found.",
        )

    def get_adjustment_investigation(self, adjustment_id: str) -> InvestigationToolResult:
        """Retrieves adjustment context, STXN, and settlement."""
        inv = self.query_engine.get_adjustment_investigation(adjustment_id)
        return InvestigationToolResult(
            tool_name="get_adjustment_investigation",
            success=inv.target_node is not None,
            structured_data={
                "adjustment_id": adjustment_id,
                "summary_facts": inv.summary_facts,
                "connected_nodes": [n.node_id for n in inv.connected_nodes],
            },
            evidence_refs=[f"adjustment:{adjustment_id}"] if inv.target_node else [],
            error=None if inv.target_node else f"Adjustment '{adjustment_id}' not found.",
        )

    def get_bank_entry_investigation(self, bank_entry_id: str) -> InvestigationToolResult:
        """Retrieves bank entry context and linked settlements."""
        inv = self.query_engine.get_bank_entry_investigation(bank_entry_id)
        return InvestigationToolResult(
            tool_name="get_bank_entry_investigation",
            success=inv.target_node is not None,
            structured_data={
                "bank_entry_id": bank_entry_id,
                "summary_facts": inv.summary_facts,
                "connected_nodes": [n.node_id for n in inv.connected_nodes],
            },
            evidence_refs=[f"bank_entry:{bank_entry_id}"] if inv.target_node else [],
            error=None if inv.target_node else f"BankEntry '{bank_entry_id}' not found.",
        )

    def get_exception_neighborhood(
        self, exception_id: Optional[str] = None, settlement_id: Optional[str] = None
    ) -> InvestigationToolResult:
        """Retrieves causal neighborhood around a specific exception or settlement exception."""
        if settlement_id:
            inv = self.query_engine.get_settlement_investigation(settlement_id)
            return InvestigationToolResult(
                tool_name="get_exception_neighborhood",
                success=True,
                structured_data={
                    "settlement_id": settlement_id,
                    "status": inv.reconciliation_status,
                    "exceptions": inv.exceptions,
                    "summary_facts": inv.summary_facts,
                    "evidence": [e.model_dump() for e in inv.evidence],
                },
                evidence_refs=[f"settlement:{settlement_id}"],
            )

        if self.recon_result and exception_id:
            for exc in self.recon_result.exceptions:
                if exc.exception_id == exception_id:
                    inv = self.query_engine.get_exception_neighborhood(exc)
                    return InvestigationToolResult(
                        tool_name="get_exception_neighborhood",
                        success=True,
                        structured_data={
                            "exception_id": exception_id,
                            "rule_code": exc.rule_code,
                            "primary_entity": f"{exc.primary_entity.entity_type}:{exc.primary_entity.entity_id}",
                            "summary_facts": inv.summary_facts,
                            "exceptions": inv.exceptions,
                        },
                        evidence_refs=[f"{exc.primary_entity.entity_type}:{exc.primary_entity.entity_id}"],
                    )

        return InvestigationToolResult(
            tool_name="get_exception_neighborhood",
            success=False,
            structured_data={},
            error="Exception or settlement could not be resolved.",
        )

    def get_graph_neighbors(self, node_id: str, direction: str = "both") -> InvestigationToolResult:
        """Returns neighbor nodes connected to node_id."""
        neighbors = get_neighbors(self.index, node_id, direction=direction)
        return InvestigationToolResult(
            tool_name="get_graph_neighbors",
            success=True,
            structured_data={
                "node_id": node_id,
                "neighbors_count": len(neighbors),
                "neighbors": [{"node_id": n.node_id, "entity_type": n.entity_type, "display_label": n.display_label} for n in neighbors],
            },
            evidence_refs=[n.node_id for n in neighbors],
        )

    def get_graph_path(self, source_node_id: str, target_node_id: str) -> InvestigationToolResult:
        """Finds causal directed path between two nodes."""
        path = find_path(self.index, source_node_id, target_node_id)
        return InvestigationToolResult(
            tool_name="get_graph_path",
            success=path is not None,
            structured_data={"source": source_node_id, "target": target_node_id, "path": path or []},
            evidence_refs=path or [],
            error=None if path is not None else f"No path from {source_node_id} to {target_node_id}.",
        )

    def get_reconciliation_evidence(self, node_id: str) -> InvestigationToolResult:
        """Retrieves reconciliation findings and rule descriptions for a specific node."""
        ev_list = self.evidence_layer.get_node_evidence(node_id)
        status = self.evidence_layer.get_node_status(node_id)
        return InvestigationToolResult(
            tool_name="get_reconciliation_evidence",
            success=True,
            structured_data={
                "node_id": node_id,
                "status": status,
                "evidence_count": len(ev_list),
                "evidence": [e.model_dump() for e in ev_list],
            },
            evidence_refs=[node_id],
        )
