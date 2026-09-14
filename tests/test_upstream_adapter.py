import pytest
from pydantic import ValidationError

from src.upstream_adapter import (
    UpstreamCustomerRecord,
    map_upstream_customer,
)


def valid_upstream_data() -> dict:
    return {
        "party_id": "C00001",
        "age_years": 35,
        "income_monthly_eur": 4200.50,
        "savings_eur": 18000.75,
        "surplus_monthly_eur": 850.25,
        "mortgage_flag": "Y",
        "credit_card_flag": "N",
        "investment_customer_flag": "Y",
        "app_visits_30d": 14,
        "marketing_permission": "N",
        "investment_permission": "Y",
        "credit_score_band": "A",
        "preferred_contact_channel": "MOBILE",
    }


def test_df_map_001_to_009_customer_fields_are_mapped_correctly():
    record = UpstreamCustomerRecord(**valid_upstream_data())

    customer = map_upstream_customer(record)

    assert customer.customer_id == "C00001"
    assert customer.age == 35
    assert customer.monthly_income == 4200.50
    assert customer.savings_balance == 18000.75
    assert customer.monthly_surplus == 850.25
    assert customer.app_visits_30d == 14
    assert customer.credit_score_band == "A"
    assert customer.preferred_channel == "MOBILE"


def test_df_map_006_boolean_flags_are_converted_correctly():
    record = UpstreamCustomerRecord(**valid_upstream_data())

    customer = map_upstream_customer(record)

    assert customer.has_mortgage is True
    assert customer.has_credit_card is False
    assert customer.investment_customer is True
    assert customer.marketing_consent is False
    assert customer.investment_consent is True


@pytest.mark.parametrize(
    "field_name",
    [
        "mortgage_flag",
        "credit_card_flag",
        "investment_customer_flag",
        "marketing_permission",
        "investment_permission",
    ],
)
def test_df_map_011_invalid_boolean_style_flags_are_rejected(field_name):
    data = valid_upstream_data()
    data[field_name] = "YES"

    with pytest.raises(ValidationError):
        UpstreamCustomerRecord(**data)


def test_df_map_010_missing_required_field_is_rejected():
    data = valid_upstream_data()
    del data["income_monthly_eur"]

    with pytest.raises(ValidationError):
        UpstreamCustomerRecord(**data)


def test_df_map_012_consent_business_meaning_is_preserved():
    data = valid_upstream_data()

    data["marketing_permission"] = "N"
    data["investment_permission"] = "Y"

    record = UpstreamCustomerRecord(**data)
    customer = map_upstream_customer(record)

    assert customer.marketing_consent is False
    assert customer.investment_consent is True