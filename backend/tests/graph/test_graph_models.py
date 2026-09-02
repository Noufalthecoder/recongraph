"""
Tests for graph data models: GraphNode, GraphEdge, FinancialGraph, and GraphEvidence.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from backend.app.graph.models import (
    FinancialGraph,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    InvestigationResult,
    InvestigationTarget,
)


def test_graph_node_immutability_and_attributes():
    """Verify GraphNode is frozen and holds deterministic ID and attributes."""
    node = GraphNode(
        node_id="payment:pay_001",
        entity_type="payment",
        entity_id="pay_001",
        display_label="Payment: pay_001 (INR 1000.00)",
        attributes={"amount": "1000.00", "currency": "INR", "status": "captured"},
    )

    assert node.node_id == "payment:pay_001"
    assert node.entity_type == "payment"
    assert node.entity_id == "pay_001"
    assert node.attributes["amount"] == "1000.00"

    # Test immutability
    with pytest.raises(ValidationError):
        node.display_label = "Modified Label"


def test_graph_edge_immutability():
    """Verify GraphEdge is frozen and correctly links source and target node IDs."""
    edge = GraphEdge(
        edge_id="edge:order:ord_001->payment:pay_001:HAS_PAYMENT",
        source_node_id="order:ord_001",
        target_node_id="payment:pay_001",
        relationship_type="HAS_PAYMENT",
        directed=True,
        attributes={"amount": "1000.00"},
    )

    assert edge.source_node_id == "order:ord_001"
    assert edge.target_node_id == "payment:pay_001"
    assert edge.relationship_type == "HAS_PAYMENT"

    with pytest.raises(ValidationError):
        edge.relationship_type = "MODIFIED"


def test_financial_graph_container():
    """Verify FinancialGraph contains nodes and edges with proper counts."""
    node1 = GraphNode(node_id="merchant:merch_1", entity_type="merchant", entity_id="merch_1", display_label="Merchant 1")
    node2 = GraphNode(node_id="order:ord_1", entity_type="order", entity_id="ord_1", display_label="Order 1")
    edge = GraphEdge(
        edge_id="edge:merchant:merch_1->order:ord_1:OWNS_ORDER",
        source_node_id="merchant:merch_1",
        target_node_id="order:ord_1",
        relationship_type="OWNS_ORDER",
    )

    graph = FinancialGraph(nodes=[node1, node2], edges=[edge])
    assert graph.node_count == 2
    assert graph.edge_count == 1
