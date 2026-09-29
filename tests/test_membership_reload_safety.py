import sqlite3

import pytest

from src.load_membership_to_sqlite import (
    ensure_base_reload_is_safe,
)
from src.membership_schema import create_membership_schema


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")

    connection.execute(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY
        )
        """
    )

    connection.execute(
        """
        INSERT INTO customers (customer_id)
        VALUES ('C00001')
        """
    )

    create_membership_schema(connection)

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
            'PLUS',
            '2025-01-01',
            NULL,
            1,
            '2025-01-01T09:00:00',
            '2026-09-21T12:00:00'
        )
        """
    )

    return connection


@pytest.mark.parametrize(
    ("table_name", "insert_sql"),
    [
        (
            "membership_events",
            """
            INSERT INTO membership_events (
                event_id,
                member_id,
                event_type,
                event_timestamp
            )
            VALUES (
                'ME000001',
                'M000001',
                'JOINED',
                '2025-01-01T09:00:00'
            )
            """,
        ),
        (
            "engagement_events",
            """
            INSERT INTO engagement_events (
                event_id,
                member_id,
                event_type,
                event_timestamp,
                channel
            )
            VALUES (
                'EE000001',
                'M000001',
                'APP_LOGIN',
                '2026-09-01T10:00:00',
                'MOBILE'
            )
            """,
        ),
        (
            "benefit_redemptions",
            """
            INSERT INTO benefit_redemptions (
                redemption_id,
                member_id,
                benefit_code,
                redemption_timestamp,
                redemption_status,
                monetary_value
            )
            VALUES (
                'BR000001',
                'M000001',
                'BENEFIT_10',
                '2026-09-01T10:00:00',
                'REDEEMED',
                10.00
            )
            """,
        ),
        (
            "campaign_interactions",
            """
            INSERT INTO campaign_interactions (
                interaction_id,
                campaign_id,
                member_id,
                channel,
                sent_timestamp,
                response_type,
                response_timestamp
            )
            VALUES (
                'CI000001',
                'CMP001',
                'M000001',
                'EMAIL',
                '2026-09-01T08:00:00',
                'OPENED',
                '2026-09-01T09:00:00'
            )
            """,
        ),
    ],
)
def test_member_cannot_be_deleted_while_child_activity_exists(
    table_name,
    insert_sql,
):
    connection = create_database()

    try:
        connection.execute(insert_sql)
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                DELETE FROM members
                WHERE member_id = 'M000001'
                """
            )

        child_count = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        assert child_count == 1

    finally:
        connection.close()


def test_base_reload_is_allowed_when_no_child_activity_exists():
    connection = create_database()

    try:
        ensure_base_reload_is_safe(
            connection
        )

    finally:
        connection.close()


@pytest.mark.parametrize(
    ("insert_sql", "expected_table"),
    [
        (
            """
            INSERT INTO membership_events (
                event_id,
                member_id,
                event_type,
                event_timestamp
            )
            VALUES (
                'ME000001',
                'M000001',
                'JOINED',
                '2025-01-01T09:00:00'
            )
            """,
            "membership_events",
        ),
        (
            """
            INSERT INTO engagement_events (
                event_id,
                member_id,
                event_type,
                event_timestamp,
                channel
            )
            VALUES (
                'EE000001',
                'M000001',
                'APP_LOGIN',
                '2026-09-01T10:00:00',
                'MOBILE'
            )
            """,
            "engagement_events",
        ),
        (
            """
            INSERT INTO benefit_redemptions (
                redemption_id,
                member_id,
                benefit_code,
                redemption_timestamp,
                redemption_status,
                monetary_value
            )
            VALUES (
                'BR000001',
                'M000001',
                'BENEFIT_10',
                '2026-09-01T10:00:00',
                'REDEEMED',
                10.00
            )
            """,
            "benefit_redemptions",
        ),
        (
            """
            INSERT INTO campaign_interactions (
                interaction_id,
                campaign_id,
                member_id,
                channel,
                sent_timestamp,
                response_type,
                response_timestamp
            )
            VALUES (
                'CI000001',
                'CMP001',
                'M000001',
                'EMAIL',
                '2026-09-01T08:00:00',
                'OPENED',
                '2026-09-01T09:00:00'
            )
            """,
            "campaign_interactions",
        ),
    ],
)
def test_base_reload_is_blocked_when_child_activity_exists(
    insert_sql,
    expected_table,
):
    connection = create_database()

    try:
        connection.execute(insert_sql)
        connection.commit()

        with pytest.raises(
            RuntimeError,
            match=expected_table,
        ):
            ensure_base_reload_is_safe(
                connection
            )

    finally:
        connection.close()