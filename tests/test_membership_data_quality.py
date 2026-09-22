import copy

import pytest

from src.load_membership_to_sqlite import (
    validate_members,
    validate_subscriptions,
)


def valid_member() -> dict:
    return {
        "member_id": "M000001",
        "customer_id": "C00001",
        "membership_status": "ACTIVE",
        "membership_tier": "PREMIUM",
        "join_date": "2025-01-01",
        "end_date": "",
        "marketing_consent": "1",
        "created_at": "2025-01-01T09:00:00",
        "updated_at": "2026-09-21T12:00:00",
    }


def valid_subscription() -> dict:
    return {
        "subscription_id": "S0000001",
        "member_id": "M000001",
        "plan_name": "MEMBERSHIP_PREMIUM",
        "start_date": "2025-01-01",
        "end_date": "",
        "renewal_status": "RENEWED",
        "auto_renew": "1",
        "price": "34.99",
        "currency": "EUR",
        "billing_frequency": "MONTHLY",
    }


def test_valid_member_is_accepted():
    accepted, rejected = validate_members(
        rows=[valid_member()],
        customer_ids={"C00001"},
    )

    assert len(accepted) == 1
    assert rejected == []


@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    [
        (
            "member_id",
            "BAD001",
            "member_id must match M######",
        ),
        (
            "customer_id",
            "C99999",
            "customer_id does not exist in customers",
        ),
        (
            "membership_status",
            "UNKNOWN",
            "invalid membership_status",
        ),
        (
            "membership_tier",
            "GOLD",
            "invalid membership_tier",
        ),
        (
            "join_date",
            "not-a-date",
            "join_date is not a valid ISO date",
        ),
        (
            "marketing_consent",
            "YES",
            "marketing_consent must be boolean-style",
        ),
        (
            "created_at",
            "",
            "created_at is missing",
        ),
        (
            "updated_at",
            "",
            "updated_at is missing",
        ),
    ],
)
def test_invalid_member_fields_are_rejected(
    field,
    value,
    expected_reason,
):
    row = valid_member()
    row[field] = value

    accepted, rejected = validate_members(
        rows=[row],
        customer_ids={"C00001"},
    )

    assert accepted == []
    assert len(rejected) == 1
    assert expected_reason in rejected[0]["reason"]
    assert rejected[0]["source"] == "members"
    assert rejected[0]["source_row_number"] == 2


def test_member_end_date_before_join_date_is_rejected():
    row = valid_member()
    row["membership_status"] = "CANCELLED"
    row["join_date"] = "2025-06-01"
    row["end_date"] = "2025-05-31"

    accepted, rejected = validate_members(
        rows=[row],
        customer_ids={"C00001"},
    )

    assert accepted == []
    assert len(rejected) == 1
    assert (
        rejected[0]["reason"]
        == "end_date precedes join_date"
    )


def test_active_member_with_end_date_is_rejected():
    row = valid_member()
    row["end_date"] = "2026-01-01"

    accepted, rejected = validate_members(
        rows=[row],
        customer_ids={"C00001"},
    )

    assert accepted == []
    assert len(rejected) == 1
    assert (
        rejected[0]["reason"]
        == "ACTIVE member must not have end_date"
    )


def test_duplicate_member_id_is_rejected():
    first = valid_member()

    second = copy.deepcopy(first)
    second["customer_id"] = "C00002"

    accepted, rejected = validate_members(
        rows=[first, second],
        customer_ids={
            "C00001",
            "C00002",
        },
    )

    assert len(accepted) == 1
    assert len(rejected) == 1

    assert (
        rejected[0]["reason"]
        == "duplicate member_id in source"
    )

    assert rejected[0]["source_row_number"] == 3


def test_multiple_memberships_for_same_customer_are_rejected():
    first = valid_member()

    second = copy.deepcopy(first)
    second["member_id"] = "M000002"

    accepted, rejected = validate_members(
        rows=[first, second],
        customer_ids={"C00001"},
    )

    assert len(accepted) == 1
    assert len(rejected) == 1

    assert (
        rejected[0]["reason"]
        == "multiple memberships for customer_id"
    )


def test_valid_subscription_is_accepted():
    accepted, rejected = validate_subscriptions(
        rows=[valid_subscription()],
        valid_member_ids={"M000001"},
    )

    assert len(accepted) == 1
    assert rejected == []


@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    [
        (
            "member_id",
            "M999999",
            "member_id does not reference an accepted member",
        ),
        (
            "renewal_status",
            "UNKNOWN",
            "invalid renewal_status",
        ),
        (
            "auto_renew",
            "YES",
            "auto_renew must be boolean-style",
        ),
        (
            "price",
            "NOT-A-NUMBER",
            "price is not numeric",
        ),
        (
            "price",
            "-9.99",
            "price must not be negative",
        ),
        (
            "currency",
            "USD",
            "unsupported currency",
        ),
        (
            "plan_name",
            "",
            "plan_name is missing",
        ),
        (
            "billing_frequency",
            "",
            "billing_frequency is missing",
        ),
    ],
)
def test_invalid_subscription_fields_are_rejected(
    field,
    value,
    expected_reason,
):
    row = valid_subscription()
    row[field] = value

    accepted, rejected = validate_subscriptions(
        rows=[row],
        valid_member_ids={"M000001"},
    )

    assert accepted == []
    assert len(rejected) == 1
    assert expected_reason in rejected[0]["reason"]
    assert rejected[0]["source"] == "subscriptions"
    assert rejected[0]["source_row_number"] == 2


def test_subscription_end_before_start_is_rejected():
    row = valid_subscription()
    row["start_date"] = "2025-06-01"
    row["end_date"] = "2025-05-31"

    accepted, rejected = validate_subscriptions(
        rows=[row],
        valid_member_ids={"M000001"},
    )

    assert accepted == []
    assert len(rejected) == 1

    assert (
        rejected[0]["reason"]
        == "end_date precedes start_date"
    )


def test_duplicate_subscription_id_is_rejected():
    first = valid_subscription()

    second = copy.deepcopy(first)

    accepted, rejected = validate_subscriptions(
        rows=[first, second],
        valid_member_ids={"M000001"},
    )

    assert len(accepted) == 1
    assert len(rejected) == 1

    assert (
        rejected[0]["reason"]
        == "duplicate subscription_id in source"
    )

    assert rejected[0]["source_row_number"] == 3