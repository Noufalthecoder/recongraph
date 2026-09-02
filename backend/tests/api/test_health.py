"""
Tests for health check endpoint.
"""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "recongraph"
