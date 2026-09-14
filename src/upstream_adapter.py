from typing import Literal

from pydantic import BaseModel

from .models import Customer


class UpstreamCustomerRecord(BaseModel):
    party_id: str
    age_years: int
    income_monthly_eur: float
    savings_eur: float
    surplus_monthly_eur: float

    mortgage_flag: Literal["Y", "N"]
    credit_card_flag: Literal["Y", "N"]
    investment_customer_flag: Literal["Y", "N"]

    app_visits_30d: int

    marketing_permission: Literal["Y", "N"]
    investment_permission: Literal["Y", "N"]

    credit_score_band: str
    preferred_contact_channel: str


def yn_to_bool(value: Literal["Y", "N"]) -> bool:
    return value == "Y"


def map_upstream_customer(record: UpstreamCustomerRecord) -> Customer:
    return Customer(
        customer_id=record.party_id,
        age=record.age_years,
        monthly_income=record.income_monthly_eur,
        savings_balance=record.savings_eur,
        monthly_surplus=record.surplus_monthly_eur,
        has_mortgage=yn_to_bool(record.mortgage_flag),
        has_credit_card=yn_to_bool(record.credit_card_flag),
        investment_customer=yn_to_bool(record.investment_customer_flag),
        app_visits_30d=record.app_visits_30d,
        marketing_consent=yn_to_bool(record.marketing_permission),
        investment_consent=yn_to_bool(record.investment_permission),
        credit_score_band=record.credit_score_band,
        preferred_channel=record.preferred_contact_channel,
    )