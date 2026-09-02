"""
Tests for benchmark metrics API endpoint.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_benchmark_api():
    res = client.get("/api/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records_processed"] >= 400
    assert data["f1"] == "1.00"
    assert data["precision"] == "1.00"
    assert data["recall"] == "1.00"
    assert len(data["anomaly_breakdown"]) >= 4
    assert "isolation_note" in data
