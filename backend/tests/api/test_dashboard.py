"""
Tests for dashboard KPI metrics and exception distribution.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_dashboard_endpoint():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()

    kpis = data["kpis"]
    assert kpis["total_records"] >= 50
    assert kpis["settlement_count"] >= 1
    assert "₹" in kpis["total_settlement_value"]
    assert "₹" in kpis["total_bank_value"]
    assert kpis["benchmark_f1"] == "1.00"

    assert "RECONCILED" in data["settlement_health"]
    assert isinstance(data["recent_exceptions"], list)
