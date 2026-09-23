from collections import Counter
from datetime import date, datetime, timedelta

from src.generate_engagement_events import (
    build_engagement_events,
)


AS_OF_DATE = date(2026, 9, 21)


VALID_CHANNELS = {
    "APP_SESSION": {
        "APP",
    },
    "CONTENT_VIEW": {
        "APP",
        "WEB",
    },
    "EMAIL_OPEN": {
        "EMAIL",
    },
    "CAMPAIGN_CLICK": {
        "EMAIL",
        "APP",
    },
    "EVENT_REGISTRATION": {
        "WEB",
        "APP",
    },
    "BENEFIT_VIEW": {
        "APP",
        "WEB",
    },
}


def member(
    member_id,
    status="ACTIVE",
    tier="STANDARD",
    join_date="2025-01-01",
    end_date=None,
):
    return {
        "member_id": member_id,
        "membership_status": status,
        "membership_tier": tier,
        "join_date": join_date,
        "end_date": end_date,
    }


def event_date(event):
    return datetime.fromisoformat(
        event["event_timestamp"]
    ).date()


def test_engagement_generation_is_deterministic():
    members = [
        member(
            "M000001",
            tier="PLUS",
        ),
        member(
            "M000002",
            status="INACTIVE",
        ),
    ]

    first = build_engagement_events(
        members=members,
        suspension_dates={},
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    second = build_engagement_events(
        members=members,
        suspension_dates={},
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    assert first == second


def test_generated_event_ids_are_unique_and_well_formed():
    members = [
        member("M000001"),
        member(
            "M000002",
            tier="PREMIUM",
        ),
    ]

    events = build_engagement_events(
        members=members,
        suspension_dates={},
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    event_ids = [
        event["event_id"]
        for event in events
    ]

    assert len(event_ids) == len(
        set(event_ids)
    )

    for event_id in event_ids:
        assert event_id.startswith(
            "EE"
        )

        assert len(event_id) == 9

        assert event_id[
            2:
        ].isdigit()


def test_generated_events_respect_member_lifecycle():
    members = [
        member(
            "M000001",
            join_date="2026-07-01",
        ),
        member(
            "M000002",
            status="CANCELLED",
            tier="PLUS",
            join_date="2025-01-01",
            end_date="2026-06-30",
        ),
        member(
            "M000003",
            status="SUSPENDED",
            tier="PREMIUM",
            join_date="2025-06-01",
        ),
    ]

    suspension_dates = {
        "M000003": date(
            2026,
            8,
            15,
        ),
    }

    events = build_engagement_events(
        members=members,
        suspension_dates=(
            suspension_dates
        ),
        as_of_date=AS_OF_DATE,
        seed=126,
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

        lifecycle_end = AS_OF_DATE

        if source_member["end_date"]:
            lifecycle_end = min(
                lifecycle_end,
                date.fromisoformat(
                    source_member[
                        "end_date"
                    ]
                ),
            )

        if (
            source_member[
                "membership_status"
            ]
            == "SUSPENDED"
        ):
            lifecycle_end = min(
                lifecycle_end,
                suspension_dates[
                    source_member[
                        "member_id"
                    ]
                ],
            )

        assert (
            join_date
            <= event_date(event)
            <= lifecycle_end
        )


def test_generated_event_channels_match_event_types():
    members = [
        member(
            "M000001",
            tier="PREMIUM",
        ),
        member(
            "M000002",
            tier="PLUS",
        ),
    ]

    events = build_engagement_events(
        members=members,
        suspension_dates={},
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    assert events

    for event in events:
        assert (
            event["event_type"]
            in VALID_CHANNELS
        )

        assert (
            event["channel"]
            in VALID_CHANNELS[
                event["event_type"]
            ]
        )


def test_status_and_tier_drive_expected_activity_ranges():
    members = [
        member(
            "M000001",
            status="ACTIVE",
            tier="STANDARD",
        ),
        member(
            "M000002",
            status="ACTIVE",
            tier="PLUS",
        ),
        member(
            "M000003",
            status="ACTIVE",
            tier="PREMIUM",
        ),
        member(
            "M000004",
            status="SUSPENDED",
            tier="STANDARD",
        ),
        member(
            "M000005",
            status="INACTIVE",
            tier="STANDARD",
        ),
        member(
            "M000006",
            status="CANCELLED",
            tier="STANDARD",
            end_date="2026-08-01",
        ),
    ]

    suspension_dates = {
        "M000004": date(
            2026,
            8,
            15,
        ),
    }

    events = build_engagement_events(
        members=members,
        suspension_dates=(
            suspension_dates
        ),
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    counts = Counter(
        event["member_id"]
        for event in events
    )

    assert (
        3
        <= counts["M000001"]
        <= 9
    )

    assert (
        4
        <= counts["M000002"]
        <= 10
    )

    assert (
        5
        <= counts["M000003"]
        <= 11
    )

    assert (
        1
        <= counts["M000004"]
        <= 4
    )

    assert (
        0
        <= counts["M000005"]
        <= 3
    )

    assert (
        1
        <= counts["M000006"]
        <= 4
    )


def test_old_members_only_generate_activity_inside_lookback_window():
    members = [
        member(
            "M000001",
            status="ACTIVE",
            tier="PREMIUM",
            join_date="2020-01-01",
        ),
    ]

    events = build_engagement_events(
        members=members,
        suspension_dates={},
        as_of_date=AS_OF_DATE,
        seed=126,
    )

    assert events

    earliest_allowed = (
        AS_OF_DATE
        - timedelta(days=180)
    )

    for event in events:
        assert (
            earliest_allowed
            <= event_date(event)
            <= AS_OF_DATE
        )