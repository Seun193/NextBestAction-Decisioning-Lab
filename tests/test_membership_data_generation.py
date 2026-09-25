from datetime import date

import numpy as np

from src.generate_membership_data import (
    build_subscriptions,
    determine_end_date,
    random_join_date,
)


def test_cancelled_members_never_generate_subscription_after_membership_end():
    members = []

    for number in range(1, 51):
        members.append(
            {
                "member_id": f"M{number:06d}",
                "membership_tier": "PREMIUM",
                "membership_status": "CANCELLED",
                "join_date": "2021-01-01",
                "end_date": "2021-03-01",
            }
        )

    subscriptions = build_subscriptions(
        members=members,
        as_of_date=date(
            2026,
            9,
            21,
        ),
        rng=np.random.default_rng(
            84
        ),
    )

    for subscription in subscriptions:
        start_date = date.fromisoformat(
            subscription[
                "start_date"
            ]
        )

        raw_end_date = subscription[
            "end_date"
        ]

        if raw_end_date:
            end_date = (
                date.fromisoformat(
                    raw_end_date
                )
            )

            assert (
                end_date
                >= start_date
            )


def test_random_join_date_can_include_as_of_date():
    class ZeroDayRng:
        def integers(
            self,
            low,
            high,
        ):
            assert low == 0
            return 0

    as_of_date = date(
        2026,
        9,
        21,
    )

    result = random_join_date(
        as_of_date=as_of_date,
        rng=ZeroDayRng(),
    )

    assert result == as_of_date


def test_recent_cancelled_member_end_date_never_precedes_join():
    class LatestDayRng:
        def integers(
            self,
            low,
            high,
        ):
            return high - 1

    join_date = date(
        2026,
        9,
        20,
    )

    as_of_date = date(
        2026,
        9,
        21,
    )

    result = determine_end_date(
        join_date=join_date,
        membership_status=(
            "CANCELLED"
        ),
        as_of_date=as_of_date,
        rng=LatestDayRng(),
    )

    assert result == as_of_date
    assert result >= join_date