import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.app import app
from src.arbitration import ArbitrationCandidate, arbitrate
from src.decision_engine import decide
from src.downstream_adapter import map_nba_to_downstream
from src.propensity_model import (
    MODEL_VERSION,
    PropensityPrediction,
    PropensityModelInput,
    predict_investment_propensity,
)
from src.upstream_adapter import (
    UpstreamCustomerRecord,
    map_upstream_customer,
)


client = TestClient(app)


def release_customer() -> UpstreamCustomerRecord:
    return UpstreamCustomerRecord(
        party_id="C90001",
        age_years=35,
        income_monthly_eur=4200.0,
        savings_eur=18000.0,
        surplus_monthly_eur=850.0,
        mortgage_flag="N",
        credit_card_flag="Y",
        investment_customer_flag="N",
        app_visits_30d=12,
        marketing_permission="Y",
        investment_permission="Y",
        credit_score_band="HIGH",
        preferred_contact_channel="MOBILE",
    )


def test_rv_001_api_health_and_version():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
    }


def test_rv_002_malformed_customer_id_is_rejected():
    response = client.get("/nba/INVALID")

    assert response.status_code == 422


def test_rv_003_upstream_identity_is_preserved():
    upstream = release_customer()

    customer = map_upstream_customer(upstream)

    assert customer.customer_id == upstream.party_id
    assert customer.monthly_income == upstream.income_monthly_eur
    assert customer.savings_balance == upstream.savings_eur


def test_rv_004_negative_marketing_consent_is_preserved():
    data = release_customer().model_dump()
    data["marketing_permission"] = "N"

    upstream = UpstreamCustomerRecord(**data)
    customer = map_upstream_customer(upstream)

    assert customer.marketing_consent is False


def test_rv_005_model_output_contract_and_version():
    model_input = PropensityModelInput(
        monthly_income=4200.0,
        savings_balance=18000.0,
        monthly_surplus=850.0,
        app_visits_30d=12,
    )

    prediction = predict_investment_propensity(model_input)

    assert 0.0 <= prediction.propensity <= 1.0
    assert prediction.model_version == MODEL_VERSION
    assert prediction.model_version == "investment-propensity-v1"

    with pytest.raises(ValidationError):
        PropensityPrediction(
            action="INVESTMENT_INFO",
            propensity=1.2,
            model_version=MODEL_VERSION,
            features={},
        )


def test_rv_006_ineligible_high_propensity_action_cannot_win():
    candidates = [
        ArbitrationCandidate(
            action="INVESTMENT_INFO",
            propensity=1.0,
            context_weight=10.0,
            business_value=10.0,
            business_lever=10.0,
            eligible=False,
            constraint_passed=True,
            priority=1,
        ),
        ArbitrationCandidate(
            action="SAVINGS_PLAN",
            propensity=0.30,
            context_weight=1.0,
            business_value=1.0,
            business_lever=1.0,
            eligible=True,
            constraint_passed=True,
            priority=2,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "SAVINGS_PLAN"


def test_rv_007_downstream_preserves_selected_nba():
    customer = map_upstream_customer(release_customer())

    decision = decide(customer)
    downstream = map_nba_to_downstream(decision)

    assert downstream.party_id == customer.customer_id
    assert downstream.selected_action_code == decision.next_best_action
    assert downstream.selected_score == decision.score
    assert downstream.selected_eligible == decision.eligible


def test_rv_008_identical_inputs_produce_consistent_results():
    upstream = release_customer()

    first_customer = map_upstream_customer(upstream)
    second_customer = map_upstream_customer(upstream)

    first_decision = decide(first_customer)
    second_decision = decide(second_customer)

    model_input = PropensityModelInput(
        monthly_income=upstream.income_monthly_eur,
        savings_balance=upstream.savings_eur,
        monthly_surplus=upstream.surplus_monthly_eur,
        app_visits_30d=upstream.app_visits_30d,
    )

    first_prediction = predict_investment_propensity(model_input)
    second_prediction = predict_investment_propensity(model_input)

    assert first_prediction.propensity == second_prediction.propensity
    assert first_decision == second_decision