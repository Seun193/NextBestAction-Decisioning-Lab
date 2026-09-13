import pytest

from src.data_quality import validate_records


def valid_record(**overrides):
    record = {
        "customer_id": "C00001",
        "age": 36,
        "monthly_income": 4500,
        "savings_balance": 18000,
        "monthly_surplus": 900,
        "has_mortgage": False,
        "has_credit_card": True,
        "investment_customer": False,
        "app_visits_30d": 12,
        "marketing_consent": True,
        "investment_consent": True,
        "credit_score_band": "HIGH",
        "preferred_channel": "MOBILE",
    }

    record.update(overrides)
    return record


def error_codes(records):
    return {
        error["code"]
        for error in validate_records(records)
    }


def test_valid_record_has_no_data_quality_errors():
    errors = validate_records([valid_record()])

    assert errors == []


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("customer_id", "", "DQ-001"),
        ("customer_id", "BAD123", "DQ-002"),
        ("age", 17, "DQ-004"),
        ("age", 76, "DQ-004"),
        ("monthly_income", 899, "DQ-005"),
        ("monthly_income", 14001, "DQ-005"),
        ("savings_balance", -1, "DQ-006"),
        ("savings_balance", 250001, "DQ-006"),
        ("monthly_surplus", -1501, "DQ-007"),
        ("monthly_surplus", 5001, "DQ-007"),
        ("app_visits_30d", -1, "DQ-008"),
        ("app_visits_30d", 51, "DQ-008"),
        ("marketing_consent", "MAYBE", "DQ-009"),
        ("credit_score_band", "VERY_HIGH", "DQ-010"),
        ("preferred_channel", "EMAIL", "DQ-011"),
    ],
)
def test_invalid_values_are_detected(
    field,
    value,
    expected_code,
):
    record = valid_record(**{field: value})

    assert expected_code in error_codes([record])


def test_duplicate_customer_id_is_detected():
    records = [
        valid_record(customer_id="C00001"),
        valid_record(customer_id="C00001"),
    ]

    assert "DQ-003" in error_codes(records)


def test_missing_required_field_is_detected():
    record = valid_record()
    del record["monthly_income"]

    assert "DQ-001" in error_codes([record])


def test_multiple_data_quality_problems_can_be_reported_together():
    record = valid_record(
        age=10,
        monthly_income=-500,
        credit_score_band="INVALID",
        preferred_channel="EMAIL",
    )

    codes = error_codes([record])

    assert "DQ-004" in codes
    assert "DQ-005" in codes
    assert "DQ-010" in codes
    assert "DQ-011" in codes
    