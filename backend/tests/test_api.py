import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_endpoint_returns_structure():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "default" in data
    assert isinstance(data["available"], dict)


def test_records_endpoint_returns_list():
    response = client.get("/api/records")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_records_404_for_unknown_id():
    response = client.get("/api/records/nonexistent_id_xyz")
    assert response.status_code == 404


def test_run_rejects_empty_message():
    response = client.post("/api/run", json={"raw_message": "", "source": "Email", "model": "claude-sonnet-4-6"})
    assert response.status_code == 422
