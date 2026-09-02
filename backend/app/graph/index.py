"""
In-memory deterministic index for fast entity and adjacency lookups on FinancialGraph.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from backend.app.graph.models import FinancialGraph, GraphEdge, GraphNode


class GraphIndex:
    """
    Provides fast, deterministic in-memory lookup indices over a FinancialGraph.
    """

    def __init__(self, graph: FinancialGraph):
        self.graph = graph

        self.nodes_by_id: Dict[str, GraphNode] = {}
        self.nodes_by_entity: Dict[Tuple[str, str], GraphNode] = {}
        self.nodes_by_type: Dict[str, List[GraphNode]] = defaultdict(list)

        self.edges_by_id: Dict[str, GraphEdge] = {}
        self.outgoing_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        self.incoming_edges: Dict[str, List[GraphEdge]] = defaultdict(list)

        self._build_index()

    def _build_index(self) -> None:
        for node in self.graph.nodes:
            self.nodes_by_id[node.node_id] = node
            self.nodes_by_entity[(node.entity_type, node.entity_id)] = node
            self.nodes_by_type[node.entity_type].append(node)

        for edge in self.graph.edges:
            self.edges_by_id[edge.edge_id] = edge
            self.outgoing_edges[edge.source_node_id].append(edge)
            self.incoming_edges[edge.target_node_id].append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes_by_id.get(node_id)

    def get_node_by_entity(self, entity_type: str, entity_id: str) -> Optional[GraphNode]:
        return self.nodes_by_entity.get((entity_type, entity_id))

    def get_merchant_node(self, merchant_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("merchant", merchant_id)

    def get_order_node(self, order_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("order", order_id)

    def get_payment_node(self, payment_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("payment", payment_id)

    def get_refund_node(self, refund_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("refund", refund_id)

    def get_adjustment_node(self, adjustment_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("adjustment", adjustment_id)

    def get_transfer_node(self, transfer_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("transfer", transfer_id)

    def get_stxn_node(self, settlement_txn_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("settlement_transaction", settlement_txn_id)

    def get_settlement_node(self, settlement_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("settlement", settlement_id)

    def get_bank_entry_node(self, bank_entry_id: str) -> Optional[GraphNode]:
        return self.get_node_by_entity("bank_entry", bank_entry_id)

    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        return self.outgoing_edges.get(node_id, [])

    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        return self.incoming_edges.get(node_id, [])
