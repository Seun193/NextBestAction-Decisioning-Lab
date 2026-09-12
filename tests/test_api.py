from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_customer_returns_404():
    response = client.get("/nba/DOES_NOT_EXIST")
    assert response.status_code == 404
