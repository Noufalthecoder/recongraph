"""
Tests for AI investigation API endpoint.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_investigation_api_query():
    # Retrieve settlements to get an existing ID
    setl_res = client.get("/api/settlements")
    setl_id = setl_res.json()["settlements"][0]["settlement_id"]

    req_body = {
        "question": f"Why is settlement {setl_id} having a discrepancy?",
        "target_type": "settlement",
        "target_id": setl_id,
    }

    res = client.post("/api/investigation", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("COMPLETED", "NEEDS_CLARIFICATION")
    assert len(data["answer"]) > 0
    assert "finding" in data
    assert isinstance(data["citations"], list)
    assert isinstance(data["recommended_next_check"], list)
