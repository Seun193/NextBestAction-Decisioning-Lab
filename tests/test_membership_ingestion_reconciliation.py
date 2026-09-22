import sqlite3

from src.load_membership_to_sqlite import (
    insert_members,
    insert_subscriptions,
    validate_members,
    validate_subscriptions,
)
from src.membership_schema import (
    create_membership_schema,
)


def create_test_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY
        )
        """
    )

    connection.executemany(
        """
        INSERT INTO customers (
            customer_id
        )
        VALUES (?)
        """,
        [
            ("C00001",),
            ("C00002",),
            ("C00003",),
        ],
    )

    create_membership_schema(
        connection
    )

    return connection


def valid_member(
    member_id: str,
    customer_id: str,
) -> dict:
    return {
        "member_id": member_id,
        "customer_id": customer_id,
        "membership_status": "ACTIVE",
        "membership_tier": "PLUS",
        "join_date": "2025-01-01",
        "end_date": "",
        "marketing_consent": "1",
        "created_at": "2025-01-01T09:00:00",
        "updated_at": "2026-09-21T12:00:00",
    }


def valid_subscription(
    subscription_id: str,
    member_id: str,
) -> dict:
    return {
        "subscription_id": subscription_id,
        "member_id": member_id,
        "plan_name": "MEMBERSHIP_PLUS",
        "start_date": "2025-01-01",
        "end_date": "",
        "renewal_status": "RENEWED",
        "auto_renew": "1",
        "price": "19.99",
        "currency": "EUR",
        "billing_frequency": "MONTHLY",
    }


def test_mixed_membership_ingestion_reconciles_source_to_database():
    connection = create_test_database()

    try:
        member_rows = [
            valid_member(
                "M000001",
                "C00001",
            ),
            {
                **valid_member(
                    "M000002",
                    "C00002",
                ),
                "membership_tier": "GOLD",
            },
            valid_member(
                "M000003",
                "C99999",
            ),
        ]

        customer_ids = {
            row[0]
            for row in connection.execute(
                """
                SELECT customer_id
                FROM customers
                """
            )
        }

        (
            accepted_members,
            rejected_members,
        ) = validate_members(
            rows=member_rows,
            customer_ids=customer_ids,
        )

        assert len(member_rows) == 3
        assert len(accepted_members) == 1
        assert len(rejected_members) == 2

        assert (
            len(member_rows)
            == len(accepted_members)
            + len(rejected_members)
        )

        accepted_member_ids = {
            row[0]
            for row in accepted_members
        }

        subscription_rows = [
            valid_subscription(
                "S0000001",
                "M000001",
            ),
            {
                **valid_subscription(
                    "S0000002",
                    "M000001",
                ),
                "price": "-5.00",
            },
            valid_subscription(
                "S0000003",
                "M999999",
            ),
        ]

        (
            accepted_subscriptions,
            rejected_subscriptions,
        ) = validate_subscriptions(
            rows=subscription_rows,
            valid_member_ids=accepted_member_ids,
        )

        assert len(subscription_rows) == 3
        assert len(accepted_subscriptions) == 1
        assert len(rejected_subscriptions) == 2

        assert (
            len(subscription_rows)
            == len(accepted_subscriptions)
            + len(rejected_subscriptions)
        )

        insert_members(
            connection,
            accepted_members,
        )

        insert_subscriptions(
            connection,
            accepted_subscriptions,
        )

        connection.commit()

        database_member_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM members
                """
            ).fetchone()[0]
        )

        database_subscription_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM subscriptions
                """
            ).fetchone()[0]
        )

        assert (
            database_member_count
            == len(accepted_members)
        )

        assert (
            database_subscription_count
            == len(accepted_subscriptions)
        )

        assert (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM members
                WHERE member_id = 'M000002'
                """
            ).fetchone()[0]
            == 0
        )

        assert (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM members
                WHERE member_id = 'M000003'
                """
            ).fetchone()[0]
            == 0
        )

        assert (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM subscriptions
                WHERE subscription_id IN (
                    'S0000002',
                    'S0000003'
                )
                """
            ).fetchone()[0]
            == 0
        )

        foreign_key_errors = list(
            connection.execute(
                "PRAGMA foreign_key_check"
            )
        )

        assert foreign_key_errors == []

        member_reasons = {
            row["reason"]
            for row in rejected_members
        }

        assert (
            "invalid membership_tier"
            in member_reasons
        )

        assert (
            "customer_id does not exist in customers"
            in member_reasons
        )

        subscription_reasons = {
            row["reason"]
            for row in rejected_subscriptions
        }

        assert (
            "price must not be negative"
            in subscription_reasons
        )

        assert (
            "member_id does not reference "
            "an accepted member"
            in subscription_reasons
        )

    finally:
        connection.close()