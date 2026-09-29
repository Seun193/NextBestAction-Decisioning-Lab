from pathlib import Path
import sqlite3

from .models import (
    Customer,
    MembershipContext,
)


DB_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "nba_lab.db"
)

MEMBERSHIP_AS_OF_DATE = "2026-09-21"


def get_connection() -> sqlite3.Connection:
    """
    Open a connection to the NBA Decisioning Lab
    SQLite database.
    """
    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"{DB_FILE} not found. "
            "Run: python -m src.load_customers_to_sqlite"
        )

    connection = sqlite3.connect(
        DB_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


def get_customer(
    customer_id: str,
) -> Customer | None:
    """
    Retrieve one customer from SQLite by customer_id.
    """

    sql = """
        SELECT
            customer_id,
            age,
            monthly_income,
            savings_balance,
            monthly_surplus,
            has_mortgage,
            has_credit_card,
            investment_customer,
            app_visits_30d,
            marketing_consent,
            investment_consent,
            credit_score_band,
            preferred_channel
        FROM customers
        WHERE customer_id = ?
    """

    with get_connection() as connection:
        row = connection.execute(
            sql,
            (
                customer_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return Customer(
        **dict(row)
    )


def get_membership_context(
    customer_id: str,
    as_of_date: str = MEMBERSHIP_AS_OF_DATE,
) -> MembershipContext | None:
    """
    Build the decisioning membership context for one customer.

    If the membership schema is not installed, return None
    so the original NBA decisioning flow can still operate.

    The trailing 30-day window is inclusive:
    as_of_date minus 29 days through as_of_date.
    """

    required_tables = {
        "members",
        "engagement_events",
        "benefit_redemptions",
        "campaign_interactions",
    }

    with get_connection() as connection:
        existing_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    if not required_tables.issubset(
        existing_tables
    ):
        return None

    sql = """
        WITH params AS (
            SELECT
                DATE(?) AS as_of_date,
                DATE(
                    ?,
                    '-29 days'
                ) AS window_start
        )

        SELECT
            m.member_id,
            m.membership_status,
            m.membership_tier,

            CAST(
                MAX(
                    0,
                    JULIANDAY(
                        CASE
                            WHEN m.end_date IS NOT NULL
                             AND DATE(m.end_date) < p.as_of_date
                            THEN DATE(m.end_date)
                            ELSE p.as_of_date
                        END
                    )
                    -
                    JULIANDAY(
                        DATE(m.join_date)
                    )
                )
                AS INTEGER
            ) AS tenure_days,

            (
                SELECT COUNT(*)
                FROM engagement_events AS e
                WHERE e.member_id = m.member_id
                  AND DATE(e.event_timestamp)
                      BETWEEN p.window_start
                          AND p.as_of_date
            ) AS engagement_events_30d,

            (
                SELECT COUNT(*)
                FROM benefit_redemptions AS b
                WHERE b.member_id = m.member_id
                  AND b.redemption_status = 'REDEEMED'
                  AND DATE(b.redemption_timestamp)
                      BETWEEN p.window_start
                          AND p.as_of_date
            ) AS successful_benefit_redemptions_30d,

            (
                SELECT COUNT(*)
                FROM campaign_interactions AS c
                WHERE c.member_id = m.member_id
                  AND DATE(c.sent_timestamp)
                      BETWEEN p.window_start
                          AND p.as_of_date
            ) AS campaign_sends_30d,

            (
                SELECT COUNT(*)
                FROM campaign_interactions AS c
                WHERE c.member_id = m.member_id
                  AND c.response_type = 'CONVERTED'
                  AND DATE(c.sent_timestamp)
                      BETWEEN p.window_start
                          AND p.as_of_date
            ) AS campaign_conversions_30d,

            (
                SELECT
                    c.response_type
                FROM campaign_interactions AS c
                WHERE c.member_id = m.member_id
                  AND DATETIME(c.sent_timestamp)
                      <= DATETIME(
                            p.as_of_date,
                            '+1 day',
                            '-1 second'
                         )
                ORDER BY
                    DATETIME(c.sent_timestamp) DESC,
                    c.interaction_id DESC
                LIMIT 1
            ) AS latest_campaign_response

        FROM members AS m

        CROSS JOIN params AS p

        WHERE m.customer_id = ?
          AND DATE(m.join_date) <= p.as_of_date
    """

    with get_connection() as connection:
        row = connection.execute(
            sql,
            (
                as_of_date,
                as_of_date,
                customer_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return MembershipContext(
        **dict(row)
    )