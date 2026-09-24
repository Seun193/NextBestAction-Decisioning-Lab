from datetime import date, datetime

from src.generate_benefit_redemptions import (
    BENEFITS,
    build_benefit_redemptions,
    tier_on_date,
)


AS_OF_DATE = date(2026, 9, 21)
SEED = 168


def make_members():
    return [
        {
            "member_id": "M000001",
            "membership_status": "ACTIVE",
            "membership_tier": "STANDARD",
            "join_date": "2026-01-01",
            "end_date": "",
        },
        {
            "member_id": "M000002",
            "membership_status": "ACTIVE",
            "membership_tier": "PREMIUM",
            "join_date": "2025-01-01",
            "end_date": "",
        },
        {
            "member_id": "M000003",
            "membership_status": "CANCELLED",
            "membership_tier": "PLUS",
            "join_date": "2025-01-01",
            "end_date": "2026-09-01",
        },
        {
            "member_id": "M000004",
            "membership_status": "SUSPENDED",
            "membership_tier": "PLUS",
            "join_date": "2025-01-01",
            "end_date": "",
        },
    ]


def make_suspension_dates():
    return {
        "M000004": date(
            2026,
            9,
            10,
        )
    }


def make_tier_history():
    return {
        "M000001": [
            (
                date(2026, 1, 1),
                "STANDARD",
            )
        ],
        "M000002": [
            (
                date(2025, 1, 1),
                "PLUS",
            ),
            (
                date(2026, 7, 1),
                "PREMIUM",
            ),
        ],
        "M000003": [
            (
                date(2025, 1, 1),
                "PLUS",
            )
        ],
        "M000004": [
            (
                date(2025, 1, 1),
                "PLUS",
            )
        ],
    }


def build_rows():
    return build_benefit_redemptions(
        members=make_members(),
        suspension_dates=(
            make_suspension_dates()
        ),
        tier_history=(
            make_tier_history()
        ),
        as_of_date=AS_OF_DATE,
        seed=SEED,
    )


def test_generation_is_deterministic():
    first = build_rows()
    second = build_rows()

    assert first == second


def test_generated_redemption_ids_are_unique_and_well_formed():
    rows = build_rows()

    ids = [
        row["redemption_id"]
        for row in rows
    ]

    assert len(ids) == len(set(ids))

    for redemption_id in ids:
        assert redemption_id.startswith(
            "BR"
        )

        assert len(redemption_id) == 9

        assert redemption_id[
            2:
        ].isdigit()


def test_generated_benefits_match_historical_tier():
    rows = build_rows()

    tier_history = (
        make_tier_history()
    )

    for row in rows:
        redemption_date = (
            datetime.fromisoformat(
                row[
                    "redemption_timestamp"
                ]
            ).date()
        )

        historical_tier = tier_on_date(
            member_id=row[
                "member_id"
            ],
            target_date=(
                redemption_date
            ),
            tier_history=(
                tier_history
            ),
        )

        assert (
            historical_tier
            in BENEFITS[
                row["benefit_code"]
            ]["tiers"]
        )


def test_successful_redemptions_never_exceed_eligibility():
    rows = build_rows()

    members = {
        member["member_id"]: member
        for member in make_members()
    }

    suspension_dates = (
        make_suspension_dates()
    )

    for row in rows:
        if (
            row["redemption_status"]
            not in {
                "REDEEMED",
                "REVERSED",
            }
        ):
            continue

        member = members[
            row["member_id"]
        ]

        redemption_date = (
            datetime.fromisoformat(
                row[
                    "redemption_timestamp"
                ]
            ).date()
        )

        if (
            member[
                "membership_status"
            ]
            in {
                "INACTIVE",
                "CANCELLED",
            }
        ):
            eligible_until = (
                date.fromisoformat(
                    member[
                        "end_date"
                    ]
                )
            )

        elif (
            member[
                "membership_status"
            ]
            == "SUSPENDED"
        ):
            eligible_until = (
                suspension_dates[
                    member[
                        "member_id"
                    ]
                ]
            )

        else:
            eligible_until = (
                AS_OF_DATE
            )

        assert (
            redemption_date
            <= eligible_until
        )


def test_failed_redemptions_have_no_monetary_value():
    rows = build_rows()

    for row in rows:
        if (
            row[
                "redemption_status"
            ]
            == "FAILED"
        ):
            assert (
                row[
                    "monetary_value"
                ]
                == ""
            )


def test_non_failed_redemptions_use_configured_value():
    rows = build_rows()

    for row in rows:
        if (
            row[
                "redemption_status"
            ]
            == "FAILED"
        ):
            continue

        expected_value = (
            BENEFITS[
                row["benefit_code"]
            ]["value"]
        )

        assert (
            float(
                row[
                    "monetary_value"
                ]
            )
            == expected_value
        )