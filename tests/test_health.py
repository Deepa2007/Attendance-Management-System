
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_healthy_status():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["application"] == "Central Attendance Management API"
    assert data["version"] == "0.1.0"
    assert data["redis"] in {"connected", "unavailable"}
