import copy
from datetime import date

from src.load_campaign_interactions_to_sqlite import (
    validate_campaign_interactions,
)


AS_OF_DATE = date(
    2026,
    9,
    21,
)


def valid_member():
    return {
        "membership_status": "ACTIVE",
        "join_date": "2026-01-01",
        "end_date": None,
        "customer_marketing_consent": "True",
    }


def valid_row():
    return {
        "interaction_id": "CI0000001",
        "campaign_id": "MEMBER_NEWS",
        "member_id": "M000001",
        "channel": "EMAIL",
        "sent_timestamp": "2026-09-10T10:00:00",
        "response_type": "OPENED",
        "response_timestamp": "2026-09-10T11:00:00",
    }


def base_members():
    return {
        "M000001": valid_member(),
    }


def base_tier_history():
    return {
        "M000001": [
            (
                date(
                    2026,
                    1,
                    1,
                ),
                "STANDARD",
            ),
        ],
    }


def validate(
    rows,
    members=None,
    suspension_dates=None,
    tier_history=None,
    as_of_date=AS_OF_DATE,
):
    return validate_campaign_interactions(
        rows=rows,
        members=(
            members
            if members is not None
            else base_members()
        ),
        suspension_dates=(
            suspension_dates
            if suspension_dates is not None
            else {}
        ),
        tier_history=(
            tier_history
            if tier_history is not None
            else base_tier_history()
        ),
        as_of_date=as_of_date,
    )


def rejection_reason(
    rejected,
):
    assert len(rejected) == 1

    return rejected[0][
        "reason"
    ]


def test_valid_campaign_interaction_is_accepted():
    accepted, rejected = validate(
        [
            valid_row(),
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_blank_response_type_and_timestamp_are_allowed():
    row = valid_row()

    row["response_type"] = ""
    row["response_timestamp"] = ""

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert len(accepted) == 1
    assert rejected == []

    assert accepted[0][5] is None
    assert accepted[0][6] is None


def test_ignored_response_without_timestamp_is_allowed():
    row = valid_row()

    row["response_type"] = (
        "IGNORED"
    )

    row["response_timestamp"] = ""

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert len(accepted) == 1
    assert rejected == []

    assert (
        accepted[0][5]
        == "IGNORED"
    )

    assert accepted[0][6] is None


def test_invalid_interaction_id_is_rejected():
    row = valid_row()

    row["interaction_id"] = (
        "BAD000001"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "interaction_id must match "
            "CI#######"
        )
    )


def test_duplicate_interaction_id_is_rejected():
    first = valid_row()

    second = copy.deepcopy(
        first
    )

    accepted, rejected = validate(
        [
            first,
            second,
        ]
    )

    assert len(accepted) == 1

    assert (
        rejection_reason(
            rejected
        )
        == (
            "duplicate interaction_id "
            "in source"
        )
    )


def test_invalid_campaign_id_is_rejected():
    row = valid_row()

    row["campaign_id"] = (
        "UNKNOWN_CAMPAIGN"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == "invalid campaign_id"
    )


def test_orphan_member_is_rejected():
    row = valid_row()

    row["member_id"] = (
        "M999999"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "member_id does not reference "
            "an existing member"
        )
    )


def test_authoritative_customer_opt_out_is_rejected():
    members = base_members()

    members[
        "M000001"
    ][
        "customer_marketing_consent"
    ] = "False"

    accepted, rejected = validate(
        [
            valid_row(),
        ],
        members=members,
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "customer marketing consent "
            "is not granted"
        )
    )


def test_invalid_campaign_channel_is_rejected():
    row = valid_row()

    row["channel"] = (
        "SMS"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "invalid channel for campaign"
        )
    )


def test_invalid_sent_timestamp_is_rejected():
    row = valid_row()

    row["sent_timestamp"] = (
        "not-a-timestamp"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        "sent_timestamp is not "
        "a valid ISO timestamp"
        in rejection_reason(
            rejected
        )
    )


def test_campaign_before_join_date_is_rejected():
    row = valid_row()

    row["sent_timestamp"] = (
        "2025-12-31T10:00:00"
    )

    row["response_timestamp"] = (
        "2025-12-31T11:00:00"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "campaign sent before "
            "join_date"
        )
    )


def test_campaign_after_as_of_date_is_rejected():
    row = valid_row()

    row["sent_timestamp"] = (
        "2026-09-22T10:00:00"
    )

    row["response_timestamp"] = (
        "2026-09-22T11:00:00"
    )

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "campaign sent after "
            "as-of date"
        )
    )


def test_campaign_after_membership_end_is_rejected():
    members = base_members()

    members[
        "M000001"
    ][
        "membership_status"
    ] = "CANCELLED"

    members[
        "M000001"
    ][
        "end_date"
    ] = "2026-09-05"

    accepted, rejected = validate(
        [
            valid_row(),
        ],
        members=members,
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "campaign sent after "
            "eligible lifecycle"
        )
    )


def test_campaign_on_membership_end_date_is_allowed():
    members = base_members()

    members[
        "M000001"
    ][
        "membership_status"
    ] = "CANCELLED"

    members[
        "M000001"
    ][
        "end_date"
    ] = "2026-09-10"

    accepted, rejected = validate(
        [
            valid_row(),
        ],
        members=members,
    )

    assert len(accepted) == 1
    assert rejected == []


def test_campaign_after_suspension_is_rejected():
    members = base_members()

    members[
        "M000001"
    ][
        "membership_status"
    ] = "SUSPENDED"

    suspension_dates = {
        "M000001": date(
            2026,
            9,
            5,
        ),
    }

    accepted, rejected = validate(
        [
            valid_row(),
        ],
        members=members,
        suspension_dates=(
            suspension_dates
        ),
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "campaign sent after "
            "eligible lifecycle"
        )
    )


def test_missing_historical_tier_is_rejected():
    accepted, rejected = validate(
        [
            valid_row(),
        ],
        tier_history={},
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "no historical tier "
            "at send time"
        )
    )


def test_premium_campaign_before_upgrade_is_rejected():
    row = valid_row()

    row[
        "campaign_id"
    ] = "PREMIUM_EXPERIENCE"

    tier_history = {
        "M000001": [
            (
                date(
                    2026,
                    1,
                    1,
                ),
                "STANDARD",
            ),
            (
                date(
                    2026,
                    9,
                    15,
                ),
                "PREMIUM",
            ),
        ],
    }

    accepted, rejected = validate(
        [
            row,
        ],
        tier_history=(
            tier_history
        ),
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "campaign is not valid "
            "for historical tier"
        )
    )


def test_premium_campaign_after_upgrade_is_allowed():
    row = valid_row()

    row[
        "campaign_id"
    ] = "PREMIUM_EXPERIENCE"

    row[
        "sent_timestamp"
    ] = "2026-09-16T10:00:00"

    row[
        "response_timestamp"
    ] = "2026-09-16T11:00:00"

    tier_history = {
        "M000001": [
            (
                date(
                    2026,
                    1,
                    1,
                ),
                "STANDARD",
            ),
            (
                date(
                    2026,
                    9,
                    15,
                ),
                "PREMIUM",
            ),
        ],
    }

    accepted, rejected = validate(
        [
            row,
        ],
        tier_history=(
            tier_history
        ),
    )

    assert len(accepted) == 1
    assert rejected == []


def test_invalid_response_type_is_rejected():
    row = valid_row()

    row[
        "response_type"
    ] = "BOUNCED"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == "invalid response_type"
    )


def test_timestamp_without_response_type_is_rejected():
    row = valid_row()

    row[
        "response_type"
    ] = ""

    row[
        "response_timestamp"
    ] = "2026-09-10T11:00:00"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "response_timestamp requires "
            "response_type"
        )
    )


def test_ignored_with_response_timestamp_is_rejected():
    row = valid_row()

    row[
        "response_type"
    ] = "IGNORED"

    row[
        "response_timestamp"
    ] = "2026-09-10T11:00:00"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "IGNORED must not have "
            "response_timestamp"
        )
    )


def test_opened_without_response_timestamp_is_rejected():
    row = valid_row()

    row[
        "response_type"
    ] = "OPENED"

    row[
        "response_timestamp"
    ] = ""

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "OPENED requires "
            "response_timestamp"
        )
    )


def test_response_at_send_time_is_rejected():
    row = valid_row()

    row[
        "response_timestamp"
    ] = row[
        "sent_timestamp"
    ]

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "response_timestamp must "
            "be after sent_timestamp"
        )
    )


def test_exact_seven_day_response_boundary_is_allowed():
    row = valid_row()

    row[
        "sent_timestamp"
    ] = "2026-09-10T10:00:00"

    row[
        "response_timestamp"
    ] = "2026-09-17T10:00:00"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_response_one_second_beyond_seven_days_is_rejected():
    row = valid_row()

    row[
        "sent_timestamp"
    ] = "2026-09-10T10:00:00"

    row[
        "response_timestamp"
    ] = "2026-09-17T10:00:01"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "response_timestamp exceeds "
            "allowed response window"
        )
    )


def test_response_after_as_of_day_is_rejected():
    row = valid_row()

    row[
        "sent_timestamp"
    ] = "2026-09-21T20:00:00"

    row[
        "response_timestamp"
    ] = "2026-09-22T00:00:00"

    accepted, rejected = validate(
        [
            row,
        ]
    )

    assert accepted == []

    assert (
        rejection_reason(
            rejected
        )
        == (
            "response_timestamp exceeds "
            "allowed response window"
        )
    )