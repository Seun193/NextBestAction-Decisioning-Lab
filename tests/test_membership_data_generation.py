from datetime import date

import numpy as np

from src.generate_membership_data import (
    build_subscriptions,
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
        as_of_date=date(2026, 9, 21),
        rng=np.random.default_rng(84),
    )

    for subscription in subscriptions:
        start_date = date.fromisoformat(
            subscription["start_date"]
        )

        raw_end_date = subscription[
            "end_date"
        ]

        if raw_end_date:
            end_date = date.fromisoformat(
                raw_end_date
            )

            assert end_date >= start_date
            