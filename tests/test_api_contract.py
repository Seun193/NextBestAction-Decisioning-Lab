import pytest
from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def test_api_001_health_contract():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
    }


def test_api_002_existing_customer_returns_valid_contract():
    response = client.get("/nba/C00001")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()

    assert set(body) == {
        "customer_id",
        "next_best_action",
        "score",
        "eligible",
        "reason_codes",
        "ranked_actions",
    }

    assert body["customer_id"] == "C00001"
    assert isinstance(body["next_best_action"], str)
    assert isinstance(body["eligible"], bool)
    assert isinstance(body["reason_codes"], list)
    assert all(isinstance(reason, str) for reason in body["reason_codes"])
    assert isinstance(body["ranked_actions"], list)


def test_api_003_unknown_valid_customer_returns_404():
    response = client.get("/nba/C99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


@pytest.mark.parametrize(
    "customer_id",
    [
        "DOES_NOT_EXIST",
        "C1234",
        "C123456",
        "X00001",
        "C12A45",
    ],
)
def test_api_004_malformed_customer_id_returns_422(customer_id):
    response = client.get(f"/nba/{customer_id}")

    assert response.status_code == 422


def test_api_005_unsupported_http_method_returns_405():
    response = client.post("/nba/C00001")

    assert response.status_code == 405


def test_api_006_unknown_endpoint_returns_404():
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404


def test_api_007_scores_are_within_contract_range():
    response = client.get("/nba/C00001")

    assert response.status_code == 200

    body = response.json()

    assert 0.0 <= body["score"] <= 1.0

    for action in body["ranked_actions"]:
        assert 0.0 <= action["score"] <= 1.0


def test_api_008_ranked_actions_match_contract():
    response = client.get("/nba/C00001")

    assert response.status_code == 200

    ranked_actions = response.json()["ranked_actions"]

    assert len(ranked_actions) == 5

    for action in ranked_actions:
        assert set(action) == {
            "action",
            "score",
            "eligible",
            "reason_codes",
        }

        assert isinstance(action["action"], str)
        assert isinstance(action["score"], (int, float))
        assert isinstance(action["eligible"], bool)
        assert isinstance(action["reason_codes"], list)
        assert all(
            isinstance(reason, str)
            for reason in action["reason_codes"]
        )


def test_api_009_success_and_error_responses_are_json():
    success_response = client.get("/nba/C00001")
    error_response = client.get("/nba/C99999")

    assert success_response.headers["content-type"].startswith(
        "application/json"
    )
    assert error_response.headers["content-type"].startswith(
        "application/json"
    )


def test_api_010_error_response_does_not_expose_internal_details():
    response = client.get("/nba/C99999")

    assert response.status_code == 404

    response_text = response.text.lower()

    forbidden_details = [
        "traceback",
        "sqlite",
        "repository.py",
        "decision_engine.py",
        "c:\\",
    ]

    for forbidden_detail in forbidden_details:
        assert forbidden_detail not in response_text