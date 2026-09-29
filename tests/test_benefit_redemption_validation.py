from datetime import date

import pytest

from src.load_benefit_redemptions_to_sqlite import (
    validate_benefit_redemptions,
)


AS_OF_DATE = date(2026, 9, 21)


def make_member(
    *,
    member_id="M000001",
    status="ACTIVE",
    join_date="2026-01-01",
    end_date="",
):
    return {
        "member_id": member_id,
        "membership_status": status,
        "join_date": join_date,
        "end_date": end_date,
    }


def make_row(
    *,
    redemption_id="BR0000001",
    member_id="M000001",
    benefit_code="WELCOME_REWARD",
    timestamp="2026-09-01T10:00:00",
    status="REDEEMED",
    monetary_value="5.00",
):
    return {
        "redemption_id": redemption_id,
        "member_id": member_id,
        "benefit_code": benefit_code,
        "redemption_timestamp": timestamp,
        "redemption_status": status,
        "monetary_value": monetary_value,
    }


def validate(
    rows,
    *,
    members=None,
    suspension_dates=None,
    tier_history=None,
):
    if members is None:
        members = {
            "M000001": make_member(),
        }

    if suspension_dates is None:
        suspension_dates = {}

    if tier_history is None:
        tier_history = {
            "M000001": [
                (
                    date(2026, 1, 1),
                    "STANDARD",
                )
            ]
        }

    return validate_benefit_redemptions(
        rows=rows,
        members=members,
        suspension_dates=suspension_dates,
        tier_history=tier_history,
        as_of_date=AS_OF_DATE,
    )


def rejection_reason(
    rejected,
):
    assert len(rejected) == 1
    return rejected[0]["reason"]


def test_valid_redeemed_redemption_is_accepted():
    accepted, rejected = validate(
        [
            make_row()
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_valid_reversed_redemption_is_accepted():
    accepted, rejected = validate(
        [
            make_row(
                status="REVERSED",
            )
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_failed_redemption_without_value_is_accepted():
    accepted, rejected = validate(
        [
            make_row(
                status="FAILED",
                monetary_value="",
            )
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_missing_redemption_id_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                redemption_id="",
            )
        ]
    )

    assert accepted == []

    assert (
        "redemption_id is missing"
        in rejection_reason(rejected)
    )


def test_bad_redemption_id_format_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                redemption_id="BAD001",
            )
        ]
    )

    assert accepted == []

    assert (
        "BR#######"
        in rejection_reason(rejected)
    )


def test_duplicate_redemption_id_is_rejected():
    rows = [
        make_row(),
        make_row(),
    ]

    accepted, rejected = validate(
        rows
    )

    assert len(accepted) == 1

    assert (
        "duplicate redemption_id"
        in rejection_reason(rejected)
    )


def test_orphan_member_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                member_id="M999999",
            )
        ]
    )

    assert accepted == []

    assert (
        "does not exist"
        in rejection_reason(rejected)
    )


def test_invalid_benefit_code_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                benefit_code="UNKNOWN",
            )
        ]
    )

    assert accepted == []

    assert (
        "invalid benefit_code"
        in rejection_reason(rejected)
    )


def test_invalid_timestamp_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                timestamp="not-a-date",
            )
        ]
    )

    assert accepted == []

    assert (
        "ISO timestamp"
        in rejection_reason(rejected)
    )


def test_invalid_status_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                status="APPROVED",
            )
        ]
    )

    assert accepted == []

    assert (
        "invalid redemption_status"
        in rejection_reason(rejected)
    )


def test_redemption_before_join_date_is_rejected():
    members = {
        "M000001": make_member(
            join_date="2026-06-01",
        )
    }

    tier_history = {
        "M000001": [
            (
                date(2026, 6, 1),
                "STANDARD",
            )
        ]
    }

    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-05-31T10:00:00",
            )
        ],
        members=members,
        tier_history=tier_history,
    )

    assert accepted == []

    assert (
        "precedes member join_date"
        in rejection_reason(rejected)
    )


def test_redemption_after_as_of_date_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-09-22T10:00:00",
            )
        ]
    )

    assert accepted == []

    assert (
        "exceeds as-of date"
        in rejection_reason(rejected)
    )


@pytest.mark.parametrize(
    "status",
    [
        "REDEEMED",
        "REVERSED",
    ],
)
def test_success_outcome_after_cancellation_is_rejected(
    status,
):
    members = {
        "M000001": make_member(
            status="CANCELLED",
            end_date="2026-09-01",
        )
    }

    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-09-05T10:00:00",
                status=status,
            )
        ],
        members=members,
    )

    assert accepted == []

    assert (
        "after eligibility ended"
        in rejection_reason(rejected)
    )


def test_failed_attempt_after_cancellation_within_30_days_is_accepted():
    members = {
        "M000001": make_member(
            status="CANCELLED",
            end_date="2026-09-01",
        )
    }

    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-09-15T10:00:00",
                status="FAILED",
                monetary_value="",
            )
        ],
        members=members,
    )

    assert len(accepted) == 1
    assert rejected == []


def test_failed_attempt_beyond_30_day_window_is_rejected():
    members = {
        "M000001": make_member(
            status="CANCELLED",
            end_date="2026-07-31",
        )
    }

    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-09-01T10:00:00",
                status="FAILED",
                monetary_value="",
            )
        ],
        members=members,
    )

    assert accepted == []

    assert (
        "post-eligibility attempt window"
        in rejection_reason(rejected)
    )


def test_redeemed_after_suspension_is_rejected():
    members = {
        "M000001": make_member(
            status="SUSPENDED",
        )
    }

    suspension_dates = {
        "M000001": date(
            2026,
            9,
            10,
        )
    }

    accepted, rejected = validate(
        [
            make_row(
                timestamp="2026-09-11T10:00:00",
            )
        ],
        members=members,
        suspension_dates=suspension_dates,
    )

    assert accepted == []

    assert (
        "after eligibility ended"
        in rejection_reason(rejected)
    )


def test_failed_redemption_with_monetary_value_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                status="FAILED",
                monetary_value="5.00",
            )
        ]
    )

    assert accepted == []

    assert (
        "must not have monetary_value"
        in rejection_reason(rejected)
    )


def test_redeemed_redemption_without_value_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                monetary_value="",
            )
        ]
    )

    assert accepted == []

    assert (
        "requires monetary_value"
        in rejection_reason(rejected)
    )


def test_wrong_monetary_value_is_rejected():
    accepted, rejected = validate(
        [
            make_row(
                monetary_value="99.00",
            )
        ]
    )

    assert accepted == []

    assert (
        "does not match benefit definition"
        in rejection_reason(rejected)
    )


def test_premium_benefit_before_upgrade_is_rejected():
    members = {
        "M000001": make_member(),
    }

    tier_history = {
        "M000001": [
            (
                date(2026, 1, 1),
                "PLUS",
            ),
            (
                date(2026, 7, 1),
                "PREMIUM",
            ),
        ]
    }

    accepted, rejected = validate(
        [
            make_row(
                benefit_code="PREMIUM_EVENT",
                timestamp="2026-06-30T10:00:00",
                monetary_value="30.00",
            )
        ],
        members=members,
        tier_history=tier_history,
    )

    assert accepted == []

    assert (
        "historical tier PLUS"
        in rejection_reason(rejected)
    )


def test_premium_benefit_after_upgrade_is_accepted():
    members = {
        "M000001": make_member(),
    }

    tier_history = {
        "M000001": [
            (
                date(2026, 1, 1),
                "PLUS",
            ),
            (
                date(2026, 7, 1),
                "PREMIUM",
            ),
        ]
    }

    accepted, rejected = validate(
        [
            make_row(
                benefit_code="PREMIUM_EVENT",
                timestamp="2026-07-02T10:00:00",
                monetary_value="30.00",
            )
        ],
        members=members,
        tier_history=tier_history,
    )

    assert len(accepted) == 1
    assert rejected == []


def test_standard_member_cannot_use_plus_benefit():
    accepted, rejected = validate(
        [
            make_row(
                benefit_code="DINING_CREDIT",
                monetary_value="12.00",
            )
        ]
    )

    assert accepted == []

    assert (
        "historical tier STANDARD"
        in rejection_reason(rejected)
    )