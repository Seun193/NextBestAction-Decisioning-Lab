from datetime import date, datetime

from src.generate_membership_events import (
    build_membership_events,
)


AS_OF_DATE = date(2026, 9, 21)


def member(
    member_id,
    status="ACTIVE",
    tier="STANDARD",
    join_date="2024-01-01",
    end_date=None,
):
    return {
        "member_id": member_id,
        "membership_status": status,
        "membership_tier": tier,
        "join_date": join_date,
        "end_date": end_date,
    }


def subscription(
    subscription_id,
    member_id,
    plan_name,
    start_date,
    end_date=None,
    renewal_status="RENEWED",
):
    return {
        "subscription_id": subscription_id,
        "member_id": member_id,
        "plan_name": plan_name,
        "start_date": start_date,
        "end_date": end_date,
        "renewal_status": renewal_status,
    }


def event_date(event):
    return datetime.fromisoformat(
        event["event_timestamp"]
    ).date()


def test_every_member_gets_exactly_one_joined_event():
    members = [
        member("M000001"),
        member(
            "M000002",
            tier="PLUS",
            join_date="2025-03-15",
        ),
        member(
            "M000003",
            status="SUSPENDED",
            tier="PREMIUM",
            join_date="2026-01-10",
        ),
    ]

    subscriptions = {
        "M000001": [],
        "M000002": [],
        "M000003": [],
    }

    events = build_membership_events(
        members=members,
        subscriptions_by_member=subscriptions,
        as_of_date=AS_OF_DATE,
    )

    joined = [
        event
        for event in events
        if event["event_type"] == "JOINED"
    ]

    assert len(joined) == len(members)

    assert {
        event["member_id"]
        for event in joined
    } == {
        "M000001",
        "M000002",
        "M000003",
    }


def test_generated_events_stay_inside_member_lifecycle():
    members = [
        member(
            "M000001",
            join_date="2024-01-01",
        ),
        member(
            "M000002",
            status="CANCELLED",
            tier="PLUS",
            join_date="2023-05-10",
            end_date="2026-05-10",
        ),
    ]

    subscriptions = {
        "M000001": [],
        "M000002": [],
    }

    events = build_membership_events(
        members=members,
        subscriptions_by_member=subscriptions,
        as_of_date=AS_OF_DATE,
    )

    member_lookup = {
        item["member_id"]: item
        for item in members
    }

    for event in events:
        source_member = member_lookup[
            event["member_id"]
        ]

        join_date = date.fromisoformat(
            source_member["join_date"]
        )

        lifecycle_end = (
            date.fromisoformat(
                source_member["end_date"]
            )
            if source_member["end_date"]
            else AS_OF_DATE
        )

        assert (
            join_date
            <= event_date(event)
            <= lifecycle_end
        )


def test_cancelled_and_suspended_members_get_terminal_events():
    members = [
        member(
            "M000001",
            status="CANCELLED",
            tier="PLUS",
            join_date="2024-01-01",
            end_date="2026-06-30",
        ),
        member(
            "M000002",
            status="SUSPENDED",
            tier="PREMIUM",
            join_date="2025-01-01",
        ),
    ]

    events = build_membership_events(
        members=members,
        subscriptions_by_member={},
        as_of_date=AS_OF_DATE,
    )

    cancelled = [
        event
        for event in events
        if (
            event["member_id"] == "M000001"
            and event["event_type"]
            == "CANCELLED"
        )
    ]

    suspended = [
        event
        for event in events
        if (
            event["member_id"] == "M000002"
            and event["event_type"]
            == "SUSPENDED"
        )
    ]

    assert len(cancelled) == 1
    assert (
        event_date(cancelled[0])
        == date(2026, 6, 30)
    )

    assert len(suspended) == 1
    assert (
        date(2025, 1, 1)
        <= event_date(suspended[0])
        <= AS_OF_DATE
    )


def test_subscription_changes_generate_upgrade_and_downgrade():
    members = [
        member(
            "M000001",
            tier="PLUS",
        ),
        member(
            "M000002",
            tier="STANDARD",
        ),
    ]

    subscriptions = {
        "M000001": [
            subscription(
                "S000001",
                "M000001",
                "MEMBERSHIP_STANDARD",
                "2024-01-01",
                "2025-01-01",
            ),
            subscription(
                "S000002",
                "M000001",
                "MEMBERSHIP_PLUS",
                "2025-01-01",
            ),
        ],
        "M000002": [
            subscription(
                "S000003",
                "M000002",
                "MEMBERSHIP_PREMIUM",
                "2024-01-01",
                "2025-01-01",
            ),
            subscription(
                "S000004",
                "M000002",
                "MEMBERSHIP_STANDARD",
                "2025-01-01",
            ),
        ],
    }

    events = build_membership_events(
        members=members,
        subscriptions_by_member=subscriptions,
        as_of_date=AS_OF_DATE,
    )

    upgrade = next(
        event
        for event in events
        if (
            event["member_id"] == "M000001"
            and event["event_type"]
            == "UPGRADED"
        )
    )

    downgrade = next(
        event
        for event in events
        if (
            event["member_id"] == "M000002"
            and event["event_type"]
            == "DOWNGRADED"
        )
    )

    assert (
        upgrade["previous_tier"]
        == "STANDARD"
    )
    assert upgrade["new_tier"] == "PLUS"

    assert (
        downgrade["previous_tier"]
        == "PREMIUM"
    )
    assert (
        downgrade["new_tier"]
        == "STANDARD"
    )


def test_renewals_stop_before_membership_end():
    members = [
        member(
            "M000001",
            status="CANCELLED",
            join_date="2023-01-01",
            end_date="2026-01-01",
        ),
    ]

    events = build_membership_events(
        members=members,
        subscriptions_by_member={},
        as_of_date=AS_OF_DATE,
    )

    renewals = [
        event
        for event in events
        if event["event_type"] == "RENEWED"
    ]

    renewal_dates = [
        event_date(event)
        for event in renewals
    ]

    assert renewal_dates == [
        date(2024, 1, 1),
        date(2025, 1, 1),
    ]

    assert date(
        2026,
        1,
        1,
    ) not in renewal_dates


def test_event_generation_is_deterministic():
    members = [
        member(
            "M000001",
            tier="PLUS",
        ),
    ]

    subscriptions = {
        "M000001": [
            subscription(
                "S000001",
                "M000001",
                "MEMBERSHIP_STANDARD",
                "2024-01-01",
                "2025-01-01",
            ),
            subscription(
                "S000002",
                "M000001",
                "MEMBERSHIP_PLUS",
                "2025-01-01",
            ),
        ],
    }

    first = build_membership_events(
        members=members,
        subscriptions_by_member=subscriptions,
        as_of_date=AS_OF_DATE,
    )

    second = build_membership_events(
        members=members,
        subscriptions_by_member=subscriptions,
        as_of_date=AS_OF_DATE,
    )

    assert first == second

    event_ids = [
        event["event_id"]
        for event in first
    ]

    assert len(event_ids) == len(
        set(event_ids)
    )