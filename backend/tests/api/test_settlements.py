"""
Tests for settlement list and detail endpoints.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_settlements_list_and_detail():
    # 1. List settlements
    res = client.get("/api/settlements")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    assert len(data["settlements"]) >= 1

    first_setl = data["settlements"][0]
    setl_id = first_setl["settlement_id"]

    # 2. Get settlement detail
    det_res = client.get(f"/api/settlements/{setl_id}")
    assert det_res.status_code == 200
    det = det_res.json()
    assert det["settlement_id"] == setl_id
    assert "₹" in det["amount"]
    assert len(det["equation_components"]) >= 1
    assert "constituent_transactions" in det


def test_settlement_detail_not_found():
    res = client.get("/api/settlements/non_existent_id")
    assert res.status_code == 404


def test_all_settlements_in_all_scenarios():
    """Verify that every settlement in every scenario loads detail and subgraph with 200 OK."""
    sc_res = client.get("/api/scenarios")
    assert sc_res.status_code == 200
    scenarios = sc_res.json()["scenarios"]

    for sc in scenarios:
        load_res = client.post(f"/api/scenarios/{sc['scenario_id']}/load")
        assert load_res.status_code == 200

        setl_res = client.get("/api/settlements")
        assert setl_res.status_code == 200
        setls = setl_res.json()["settlements"]

        for s in setls:
            sid = s["settlement_id"]
            # Detail endpoint
            d_res = client.get(f"/api/settlements/{sid}")
            assert d_res.status_code == 200, f"Failed settlement detail for {sid} in scenario {sc['scenario_id']}"
            detail = d_res.json()
            assert detail["settlement_id"] == sid
            assert isinstance(detail["equation_components"], list)
            assert isinstance(detail["exceptions"], list)
            assert isinstance(detail["evidence"], list)

            # Subgraph endpoint
            g_res = client.get(f"/api/graph/settlements/{sid}")
            assert g_res.status_code == 200, f"Failed subgraph for {sid} in scenario {sc['scenario_id']}"
            graph = g_res.json()
            assert "nodes" in graph
            assert "edges" in graph

