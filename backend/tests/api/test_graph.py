"""
Tests for graph endpoints.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_full_graph_and_subgraph():
    # 1. Full graph
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] >= 20
    assert data["total_edges"] >= 20
    assert len(data["nodes"]) == data["total_nodes"]

    # 2. Settlement focused subgraph
    setl_res = client.get("/api/settlements")
    setl_id = setl_res.json()["settlements"][0]["settlement_id"]

    sub_res = client.get(f"/api/graph/settlements/{setl_id}")
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["total_nodes"] >= 2
    assert any(n["entity_id"] == setl_id for n in sub_data["nodes"])
