"""
Data models for the deterministic Financial Investigation Graph.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.common import MoneyDecimal


class GraphNode(BaseModel):
    """
    Immutable representation of an entity node in the financial graph.

    Deterministic node ID format: '<entity_type>:<entity_id>'
    e.g. 'merchant:merch_001', 'settlement:setl_1001', 'payment:pay_5001'
    """
    model_config = ConfigDict(frozen=True)

    node_id: str
    entity_type: str
    entity_id: str
    display_label: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """
    Immutable representation of a directed relationship edge between two nodes.

    Deterministic edge ID format: 'edge:<source_node_id>-><target_node_id>:<rel_type>'
    """
    model_config = ConfigDict(frozen=True)

    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    directed: bool = True
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEvidence(BaseModel):
    """
    Deterministic reconciliation and audit evidence attached to a graph node or edge.
    """
    model_config = ConfigDict(frozen=True)

    status: str
    rule_code: str
    severity: str
    explanation: str
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    difference: Optional[MoneyDecimal] = None
    related_node_ids: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class FinancialGraph(BaseModel):
    """
    Complete immutable financial relationship graph.
    """
    model_config = ConfigDict(frozen=True)

    nodes: List[GraphNode]
    edges: List[GraphEdge]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


class InvestigationTarget(BaseModel):
    """Specifies the starting target entity for an investigation query."""
    model_config = ConfigDict(frozen=True)

    entity_type: str
    entity_id: str


class InvestigationResult(BaseModel):
    """
    Immutable outcome of a graph investigation query.
    """
    model_config = ConfigDict(frozen=True)

    target: InvestigationTarget
    target_node: Optional[GraphNode] = None
    connected_nodes: List[GraphNode] = Field(default_factory=list)
    connected_edges: List[GraphEdge] = Field(default_factory=list)
    reconciliation_status: str
    evidence: List[GraphEvidence] = Field(default_factory=list)
    exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    summary_facts: Dict[str, Any] = Field(default_factory=dict)
