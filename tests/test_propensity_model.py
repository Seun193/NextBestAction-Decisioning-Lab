import pytest
from pydantic import ValidationError

from src.arbitration import ArbitrationCandidate, arbitrate
from src.propensity_model import (
    MODEL_VERSION,
    PropensityModelInput,
    predict_investment_propensity,
)


def model_input(
    monthly_income: float = 4000.0,
    savings_balance: float = 10000.0,
    monthly_surplus: float = 600.0,
    app_visits_30d: int = 10,
) -> PropensityModelInput:
    return PropensityModelInput(
        monthly_income=monthly_income,
        savings_balance=savings_balance,
        monthly_surplus=monthly_surplus,
        app_visits_30d=app_visits_30d,
    )


def test_pm_001_propensity_is_between_zero_and_one():
    prediction = predict_investment_propensity(model_input())

    assert 0.0 <= prediction.propensity <= 1.0


def test_pm_002_prediction_is_deterministic():
    data = model_input()

    first = predict_investment_propensity(data)
    second = predict_investment_propensity(data)

    assert first.propensity == second.propensity


def test_pm_003_model_version_is_exposed():
    prediction = predict_investment_propensity(model_input())

    assert prediction.model_version == MODEL_VERSION
    assert prediction.model_version == "investment-propensity-v1"


def test_pm_004_scoring_features_are_exposed():
    prediction = predict_investment_propensity(model_input())

    assert prediction.features["monthly_income"] == 4000.0
    assert prediction.features["savings_balance"] == 10000.0
    assert prediction.features["monthly_surplus"] == 600.0
    assert prediction.features["app_visits_30d"] == 10.0


def test_pm_005_higher_savings_does_not_reduce_propensity():
    lower = predict_investment_propensity(
        model_input(savings_balance=1000.0)
    )

    higher = predict_investment_propensity(
        model_input(savings_balance=20000.0)
    )

    assert higher.propensity >= lower.propensity


def test_pm_006_higher_surplus_does_not_reduce_propensity():
    lower = predict_investment_propensity(
        model_input(monthly_surplus=100.0)
    )

    higher = predict_investment_propensity(
        model_input(monthly_surplus=1200.0)
    )

    assert higher.propensity >= lower.propensity


def test_pm_007_more_engagement_does_not_reduce_propensity():
    lower = predict_investment_propensity(
        model_input(app_visits_30d=1)
    )

    higher = predict_investment_propensity(
        model_input(app_visits_30d=30)
    )

    assert higher.propensity >= lower.propensity


@pytest.mark.parametrize(
    "field_name, invalid_value",
    [
        ("monthly_income", 0.0),
        ("savings_balance", -1.0),
        ("app_visits_30d", -1),
    ],
)
def test_pm_008_invalid_model_input_is_rejected(
    field_name,
    invalid_value,
):
    values = {
        "monthly_income": 4000.0,
        "savings_balance": 10000.0,
        "monthly_surplus": 600.0,
        "app_visits_30d": 10,
    }

    values[field_name] = invalid_value

    with pytest.raises(ValidationError):
        PropensityModelInput(**values)


def test_pm_009_high_propensity_does_not_override_eligibility():
    prediction = predict_investment_propensity(
        model_input(
            savings_balance=50000.0,
            monthly_surplus=3000.0,
            app_visits_30d=50,
        )
    )

    candidates = [
        ArbitrationCandidate(
            action="INVESTMENT_INFO",
            propensity=prediction.propensity,
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


def test_pm_010_prediction_integrates_with_arbitration():
    prediction = predict_investment_propensity(
        model_input(
            savings_balance=20000.0,
            monthly_surplus=1000.0,
            app_visits_30d=20,
        )
    )

    candidates = [
        ArbitrationCandidate(
            action="INVESTMENT_INFO",
            propensity=prediction.propensity,
            context_weight=1.0,
            business_value=2.0,
            business_lever=1.0,
            eligible=True,
            constraint_passed=True,
            priority=1,
        ),
        ArbitrationCandidate(
            action="SAVINGS_PLAN",
            propensity=0.20,
            context_weight=1.0,
            business_value=1.0,
            business_lever=1.0,
            eligible=True,
            constraint_passed=True,
            priority=2,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "INVESTMENT_INFO"    