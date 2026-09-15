import math

from pydantic import BaseModel, Field


MODEL_VERSION = "investment-propensity-v1"


class PropensityModelInput(BaseModel):
    monthly_income: float = Field(gt=0)
    savings_balance: float = Field(ge=0)
    monthly_surplus: float
    app_visits_30d: int = Field(ge=0)


class PropensityPrediction(BaseModel):
    action: str
    propensity: float = Field(ge=0.0, le=1.0)
    model_version: str
    features: dict[str, float]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def predict_investment_propensity(
    model_input: PropensityModelInput,
) -> PropensityPrediction:
    savings_ratio = min(
        model_input.savings_balance / model_input.monthly_income,
        5.0,
    )

    surplus_ratio = max(
        -1.0,
        min(
            model_input.monthly_surplus / model_input.monthly_income,
            1.0,
        ),
    )

    engagement = min(
        float(model_input.app_visits_30d),
        50.0,
    )

    linear_score = (
        -2.2
        + (0.35 * savings_ratio)
        + (1.40 * surplus_ratio)
        + (0.04 * engagement)
    )

    propensity = _sigmoid(linear_score)

    return PropensityPrediction(
        action="INVESTMENT_INFO",
        propensity=propensity,
        model_version=MODEL_VERSION,
        features={
            "monthly_income": model_input.monthly_income,
            "savings_balance": model_input.savings_balance,
            "monthly_surplus": model_input.monthly_surplus,
            "app_visits_30d": float(model_input.app_visits_30d),
            "savings_ratio": savings_ratio,
            "surplus_ratio": surplus_ratio,
        },
    )