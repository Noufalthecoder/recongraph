"""
Deterministic graph traversal algorithms for the FinancialGraph.
"""

from collections import deque
from typing import List, Optional, Set, Tuple

from backend.app.graph.index import GraphIndex
from backend.app.graph.models import GraphEdge, GraphNode


def get_neighbors(index: GraphIndex, node_id: str, direction: str = "both") -> List[GraphNode]:
    """
    Returns immediate neighbor nodes connected in the specified direction ('outgoing', 'incoming', 'both').
    Sorted deterministically.
    """
    neighbor_ids: Set[str] = set()

    if direction in ("outgoing", "both"):
        for edge in index.get_outgoing_edges(node_id):
            neighbor_ids.add(edge.target_node_id)

    if direction in ("incoming", "both"):
        for edge in index.get_incoming_edges(node_id):
            neighbor_ids.add(edge.source_node_id)

    nodes = [index.get_node(nid) for nid in neighbor_ids if index.get_node(nid) is not None]
    return sorted(nodes, key=lambda n: (n.entity_type, n.entity_id, n.node_id))


def get_ancestors(index: GraphIndex, node_id: str) -> List[GraphNode]:
    """
    Traverses backwards along incoming edges to find all ancestor nodes.
    Cycle-safe and deterministically sorted.
    """
    visited: Set[str] = set()
    queue = deque([node_id])

    while queue:
        curr = queue.popleft()
        for edge in index.get_incoming_edges(curr):
            src = edge.source_node_id
            if src not in visited and src != node_id:
                visited.add(src)
                queue.append(src)

    nodes = [index.get_node(nid) for nid in visited if index.get_node(nid) is not None]
    return sorted(nodes, key=lambda n: (n.entity_type, n.entity_id, n.node_id))


def get_descendants(index: GraphIndex, node_id: str) -> List[GraphNode]:
    """
    Traverses forwards along outgoing edges to find all descendant nodes.
    Cycle-safe and deterministically sorted.
    """
    visited: Set[str] = set()
    queue = deque([node_id])

    while queue:
        curr = queue.popleft()
        for edge in index.get_outgoing_edges(curr):
            tgt = edge.target_node_id
            if tgt not in visited and tgt != node_id:
                visited.add(tgt)
                queue.append(tgt)

    nodes = [index.get_node(nid) for nid in visited if index.get_node(nid) is not None]
    return sorted(nodes, key=lambda n: (n.entity_type, n.entity_id, n.node_id))


def get_subgraph(
    index: GraphIndex,
    node_id: str,
    max_depth: int = 3,
) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """
    Extracts the bidirectional neighborhood subgraph surrounding node_id up to max_depth.
    Returns (nodes, edges) sorted deterministically.
    """
    if index.get_node(node_id) is None:
        return [], []

    visited_nodes: Set[str] = {node_id}
    queue: deque[Tuple[str, int]] = deque([(node_id, 0)])

    while queue:
        curr_id, depth = queue.popleft()
        if depth >= max_depth:
            continue

        # Outgoing
        for edge in index.get_outgoing_edges(curr_id):
            tgt = edge.target_node_id
            if tgt not in visited_nodes:
                visited_nodes.add(tgt)
                queue.append((tgt, depth + 1))

        # Incoming
        for edge in index.get_incoming_edges(curr_id):
            src = edge.source_node_id
            if src not in visited_nodes:
                visited_nodes.add(src)
                queue.append((src, depth + 1))

    # Collect all edges where both endpoints are in visited_nodes
    subgraph_edges: List[GraphEdge] = []
    for nid in visited_nodes:
        for edge in index.get_outgoing_edges(nid):
            if edge.target_node_id in visited_nodes:
                subgraph_edges.append(edge)

    nodes = [index.get_node(nid) for nid in visited_nodes if index.get_node(nid) is not None]
    sorted_nodes = sorted(nodes, key=lambda n: (n.entity_type, n.entity_id, n.node_id))
    sorted_edges = sorted(
        subgraph_edges,
        key=lambda e: (e.source_node_id, e.target_node_id, e.relationship_type, e.edge_id),
    )

    return sorted_nodes, sorted_edges


def find_path(
    index: GraphIndex,
    source_node_id: str,
    target_node_id: str,
) -> Optional[List[str]]:
    """
    Finds the shortest directed path from source_node_id to target_node_id using BFS.
    Returns list of node IDs in sequence or None if no path exists.
    """
    if index.get_node(source_node_id) is None or index.get_node(target_node_id) is None:
        return None

    if source_node_id == target_node_id:
        return [source_node_id]

    visited: Set[str] = {source_node_id}
    queue: deque[List[str]] = deque([[source_node_id]])

    while queue:
        path = queue.popleft()
        curr = path[-1]

        for edge in index.get_outgoing_edges(curr):
            tgt = edge.target_node_id
            if tgt == target_node_id:
                return path + [tgt]
            if tgt not in visited:
                visited.add(tgt)
                queue.append(path + [tgt])

    return None
