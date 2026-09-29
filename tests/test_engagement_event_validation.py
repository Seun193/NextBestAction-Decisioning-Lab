import sqlite3
from datetime import date

import pytest

from src.load_engagement_events_to_sqlite import (
    insert_events,
    validate_engagement_events,
)
from src.membership_schema import (
    create_membership_schema,
)


AS_OF_DATE = date(2026, 9, 21)


MEMBERS = {
    "M000001": {
        "member_id": "M000001",
        "membership_status": "ACTIVE",
        "join_date": "2025-01-01",
        "end_date": None,
    },
    "M000002": {
        "member_id": "M000002",
        "membership_status": "CANCELLED",
        "join_date": "2024-01-01",
        "end_date": "2026-06-30",
    },
    "M000003": {
        "member_id": "M000003",
        "membership_status": "SUSPENDED",
        "join_date": "2025-06-01",
        "end_date": None,
    },
}


SUSPENSION_DATES = {
    "M000003": date(
        2026,
        8,
        15,
    ),
}


def make_event(**overrides) -> dict:
    event = {
        "event_id": "EE0000001",
        "member_id": "M000001",
        "event_type": "APP_SESSION",
        "event_timestamp": (
            "2026-09-01T10:00:00"
        ),
        "channel": "APP",
    }

    event.update(overrides)

    return event


def validate(rows):
    return validate_engagement_events(
        rows=rows,
        members=MEMBERS,
        suspension_dates=(
            SUSPENSION_DATES
        ),
        as_of_date=AS_OF_DATE,
    )


@pytest.mark.parametrize(
    ("event_type", "channel"),
    [
        (
            "APP_SESSION",
            "APP",
        ),
        (
            "CONTENT_VIEW",
            "WEB",
        ),
        (
            "EMAIL_OPEN",
            "EMAIL",
        ),
        (
            "CAMPAIGN_CLICK",
            "EMAIL",
        ),
        (
            "EVENT_REGISTRATION",
            "APP",
        ),
        (
            "BENEFIT_VIEW",
            "WEB",
        ),
    ],
)
def test_valid_event_channel_pair_is_accepted(
    event_type,
    channel,
):
    accepted, rejected = validate(
        [
            make_event(
                event_type=event_type,
                channel=channel,
            ),
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


@pytest.mark.parametrize(
    ("overrides", "expected_reason"),
    [
        (
            {
                "event_id": "",
            },
            "event_id is missing",
        ),
        (
            {
                "event_id": "BAD001",
            },
            "event_id must match EE#######",
        ),
        (
            {
                "member_id": "",
            },
            "member_id is missing",
        ),
        (
            {
                "member_id": "M999999",
            },
            (
                "member_id does not exist "
                "in members"
            ),
        ),
        (
            {
                "event_type": "UNKNOWN",
            },
            "invalid event_type",
        ),
        (
            {
                "event_timestamp": "",
            },
            "event_timestamp is missing",
        ),
        (
            {
                "event_timestamp": (
                    "not-a-timestamp"
                ),
            },
            (
                "event_timestamp is not "
                "a valid ISO timestamp"
            ),
        ),
        (
            {
                "channel": "",
            },
            "channel is missing",
        ),
        (
            {
                "event_type": (
                    "APP_SESSION"
                ),
                "channel": "WEB",
            },
            (
                "invalid channel WEB "
                "for APP_SESSION"
            ),
        ),
        (
            {
                "event_timestamp": (
                    "2024-12-31T10:00:00"
                ),
            },
            (
                "event precedes member "
                "join_date"
            ),
        ),
        (
            {
                "event_timestamp": (
                    "2026-09-22T10:00:00"
                ),
            },
            (
                "event exceeds member "
                "activity lifecycle"
            ),
        ),
        (
            {
                "member_id": "M000002",
                "event_timestamp": (
                    "2026-07-01T10:00:00"
                ),
            },
            (
                "event exceeds member "
                "activity lifecycle"
            ),
        ),
        (
            {
                "member_id": "M000003",
                "event_timestamp": (
                    "2026-08-16T10:00:00"
                ),
            },
            (
                "event exceeds member "
                "activity lifecycle"
            ),
        ),
    ],
)
def test_invalid_engagement_event_is_rejected(
    overrides,
    expected_reason,
):
    accepted, rejected = validate(
        [
            make_event(
                **overrides
            ),
        ]
    )

    assert accepted == []
    assert len(rejected) == 1

    assert expected_reason in (
        rejected[0]["reason"]
    )


def test_event_on_cancellation_date_is_allowed():
    accepted, rejected = validate(
        [
            make_event(
                member_id="M000002",
                event_timestamp=(
                    "2026-06-30T12:00:00"
                ),
            ),
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_event_on_suspension_date_is_allowed():
    accepted, rejected = validate(
        [
            make_event(
                member_id="M000003",
                event_timestamp=(
                    "2026-08-15T12:00:00"
                ),
            ),
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_duplicate_event_id_is_rejected():
    rows = [
        make_event(),
        make_event(
            event_type="CONTENT_VIEW",
            event_timestamp=(
                "2026-09-02T11:00:00"
            ),
            channel="WEB",
        ),
    ]

    accepted, rejected = validate(
        rows
    )

    assert len(accepted) == 1
    assert len(rejected) == 1

    assert (
        rejected[0]["reason"]
        == "duplicate event_id in source"
    )


def test_engagement_ingestion_reconciles_source_and_database():
    connection = sqlite3.connect(
        ":memory:"
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:
        connection.execute(
            """
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY
            )
            """
        )

        connection.execute(
            """
            INSERT INTO customers (
                customer_id
            )
            VALUES ('C00001')
            """
        )

        create_membership_schema(
            connection
        )

        connection.execute(
            """
            INSERT INTO members (
                member_id,
                customer_id,
                membership_status,
                membership_tier,
                join_date,
                end_date,
                marketing_consent,
                created_at,
                updated_at
            )
            VALUES (
                'M000001',
                'C00001',
                'ACTIVE',
                'STANDARD',
                '2025-01-01',
                NULL,
                1,
                '2025-01-01T09:00:00',
                '2026-09-21T12:00:00'
            )
            """
        )

        rows = [
            make_event(),
            make_event(
                event_id="EE0000002",
                member_id="M999999",
            ),
        ]

        accepted, rejected = (
            validate_engagement_events(
                rows=rows,
                members={
                    "M000001": MEMBERS[
                        "M000001"
                    ]
                },
                suspension_dates={},
                as_of_date=(
                    AS_OF_DATE
                ),
            )
        )

        insert_events(
            connection,
            accepted,
        )

        connection.commit()

        database_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM engagement_events
                """
            ).fetchone()[0]
        )

        foreign_key_errors = list(
            connection.execute(
                "PRAGMA foreign_key_check"
            )
        )

        assert len(rows) == 2
        assert len(accepted) == 1
        assert len(rejected) == 1

        assert (
            len(rows)
            == len(accepted)
            + len(rejected)
        )

        assert (
            database_count
            == len(accepted)
        )

        assert database_count == 1

        assert (
            foreign_key_errors
            == []
        )

    finally:
        connection.close()