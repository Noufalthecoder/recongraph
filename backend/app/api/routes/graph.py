"""
Financial relationship graph routes.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import GraphEdgeDTO, GraphNodeDTO, GraphResponse

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def get_full_graph():
    bundle = demo_state.active_scenario
    graph = bundle.graph
    ev_layer = bundle.evidence_layer

    nodes: List[GraphNodeDTO] = []
    for n in graph.nodes:
        status = ev_layer.get_node_status(n.node_id)
        nodes.append(
            GraphNodeDTO(
                node_id=n.node_id,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                display_label=n.display_label,
                status=status,
                attributes=n.attributes,
            )
        )

    edges: List[GraphEdgeDTO] = []
    for e in graph.edges:
        edges.append(
            GraphEdgeDTO(
                edge_id=e.edge_id,
                source=e.source_node_id,
                target=e.target_node_id,
                relationship_type=e.relationship_type,
                directed=e.directed,
                attributes=e.attributes,
            )
        )

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/settlements/{settlement_id}", response_model=GraphResponse)
def get_settlement_subgraph(settlement_id: str):
    bundle = demo_state.active_scenario
    inv = bundle.query_engine.get_settlement_investigation(settlement_id)
    ev_layer = bundle.evidence_layer

    if not inv.target_node:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement '{settlement_id}' not found in graph.",
        )

    subgraph_nodes = [inv.target_node] + inv.connected_nodes
    node_ids = {n.node_id for n in subgraph_nodes}

    nodes: List[GraphNodeDTO] = []
    for n in subgraph_nodes:
        status = ev_layer.get_node_status(n.node_id)
        nodes.append(
            GraphNodeDTO(
                node_id=n.node_id,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                display_label=n.display_label,
                status=status,
                attributes=n.attributes,
            )
        )

    edges: List[GraphEdgeDTO] = []
    for e in inv.connected_edges:
        edges.append(
            GraphEdgeDTO(
                edge_id=e.edge_id,
                source=e.source_node_id,
                target=e.target_node_id,
                relationship_type=e.relationship_type,
                directed=e.directed,
                attributes=e.attributes,
            )
        )

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )
