import sqlite3
from datetime import date

import pytest

from src.load_membership_events_to_sqlite import (
    insert_events,
    validate_membership_events,
)
from src.membership_schema import create_membership_schema


AS_OF_DATE = date(2026, 9, 21)


MEMBERS = {
    "M000001": {
        "member_id": "M000001",
        "membership_status": "ACTIVE",
        "membership_tier": "STANDARD",
        "join_date": "2025-01-01",
        "end_date": None,
    },
    "M000002": {
        "member_id": "M000002",
        "membership_status": "CANCELLED",
        "membership_tier": "PLUS",
        "join_date": "2024-01-01",
        "end_date": "2026-06-30",
    },
    "M000003": {
        "member_id": "M000003",
        "membership_status": "SUSPENDED",
        "membership_tier": "PREMIUM",
        "join_date": "2025-06-01",
        "end_date": None,
    },
}


def make_event(**overrides) -> dict:
    event = {
        "event_id": "ME0000001",
        "member_id": "M000001",
        "event_type": "JOINED",
        "event_timestamp": "2025-01-01T09:00:00",
        "previous_tier": "",
        "new_tier": "STANDARD",
        "notes": "Membership created",
    }

    event.update(overrides)

    return event


def validate(rows):
    return validate_membership_events(
        rows=rows,
        members=MEMBERS,
        as_of_date=AS_OF_DATE,
    )


def test_valid_joined_event_is_accepted():
    accepted, rejected = validate(
        [
            make_event(),
        ]
    )

    assert len(accepted) == 1
    assert rejected == []


def test_valid_upgrade_event_is_accepted():
    accepted, rejected = validate(
        [
            make_event(
                event_type="UPGRADED",
                event_timestamp="2026-01-01T11:00:00",
                previous_tier="STANDARD",
                new_tier="PLUS",
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
                "event_id": "BAD001",
            },
            "event_id must match ME#######",
        ),
        (
            {
                "member_id": "M999999",
            },
            "member_id does not exist in members",
        ),
        (
            {
                "event_type": "UNKNOWN",
            },
            "invalid event_type",
        ),
        (
            {
                "event_timestamp": "not-a-timestamp",
            },
            "event_timestamp is not a valid ISO timestamp",
        ),
        (
            {
                "event_timestamp": "2024-12-31T09:00:00",
            },
            "event precedes member join_date",
        ),
        (
            {
                "event_type": "RENEWED",
                "event_timestamp": "2026-09-22T10:00:00",
                "new_tier": "",
            },
            "event exceeds member lifecycle",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "GOLD",
                "new_tier": "PLUS",
            },
            "invalid previous_tier",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "STANDARD",
                "new_tier": "GOLD",
            },
            "invalid new_tier",
        ),
        (
            {
                "event_timestamp": "2025-01-02T09:00:00",
            },
            "JOINED event must occur on join_date",
        ),
        (
            {
                "new_tier": "",
            },
            "JOINED event requires new_tier",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "",
                "new_tier": "PLUS",
            },
            "UPGRADED requires previous_tier",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "STANDARD",
                "new_tier": "",
            },
            "UPGRADED requires new_tier",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "PLUS",
                "new_tier": "PLUS",
            },
            "UPGRADED tiers must differ",
        ),
        (
            {
                "event_type": "UPGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "PREMIUM",
                "new_tier": "PLUS",
            },
            "UPGRADED event does not increase tier",
        ),
        (
            {
                "event_type": "DOWNGRADED",
                "event_timestamp": "2026-01-01T11:00:00",
                "previous_tier": "STANDARD",
                "new_tier": "PLUS",
            },
            "DOWNGRADED event does not decrease tier",
        ),
        (
            {
                "event_type": "CANCELLED",
                "event_timestamp": "2026-01-01T17:00:00",
                "previous_tier": "STANDARD",
                "new_tier": "",
            },
            "CANCELLED event requires member end_date",
        ),
        (
            {
                "member_id": "M000002",
                "event_type": "CANCELLED",
                "event_timestamp": "2026-06-29T17:00:00",
                "previous_tier": "PLUS",
                "new_tier": "",
            },
            "CANCELLED event must occur on member end_date",
        ),
    ],
)
def test_invalid_membership_event_is_rejected(
    overrides,
    expected_reason,
):
    accepted, rejected = validate(
        [
            make_event(**overrides),
        ]
    )

    assert accepted == []
    assert len(rejected) == 1
    assert expected_reason in rejected[0]["reason"]


def test_duplicate_event_id_is_rejected():
    rows = [
        make_event(),
        make_event(
            event_type="RENEWED",
            event_timestamp="2026-01-01T10:00:00",
            new_tier="",
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


def test_event_ingestion_reconciles_source_and_database():
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
                event_id="ME0000002",
                member_id="M999999",
            ),
        ]

        accepted, rejected = (
            validate_membership_events(
                rows=rows,
                members={
                    "M000001": MEMBERS[
                        "M000001"
                    ]
                },
                as_of_date=AS_OF_DATE,
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
                FROM membership_events
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

        assert database_count == 1
        assert database_count == len(
            accepted
        )

        assert foreign_key_errors == []

    finally:
        connection.close()