"""
Tests for scenario catalogue and loading.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_list_and_load_scenarios():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) >= 5
    assert data["active_scenario_id"] == "production_demo"

    # Switch to clean batch
    load_res = client.post("/api/scenarios/clean_batch/load")
    assert load_res.status_code == 200
    load_data = load_res.json()
    assert load_data["active_scenario_id"] == "clean_batch"

    # Switch back to production demo
    client.post("/api/scenarios/production_demo/load")
