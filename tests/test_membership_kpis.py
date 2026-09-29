import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

KPI_SQL_PATH = (
    ROOT
    / "sql"
    / "membership_kpis.sql"
)


@pytest.fixture
def kpi_database(
    tmp_path: Path,
):
    database_path = (
        tmp_path
        / "membership_kpi_test.db"
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            marketing_consent TEXT
        );

        CREATE TABLE members (
            member_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            membership_status TEXT NOT NULL,
            membership_tier TEXT NOT NULL,
            join_date TEXT NOT NULL,
            end_date TEXT,
            marketing_consent INTEGER NOT NULL
        );

        CREATE TABLE subscriptions (
            subscription_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            renewal_status TEXT NOT NULL,
            auto_renew INTEGER NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            billing_frequency TEXT NOT NULL
        );

        CREATE TABLE membership_events (
            event_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL
        );

        CREATE TABLE engagement_events (
            event_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            event_timestamp TEXT NOT NULL
        );

        CREATE TABLE benefit_redemptions (
            redemption_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            redemption_status TEXT NOT NULL,
            redemption_timestamp TEXT NOT NULL
        );

        CREATE TABLE campaign_interactions (
            interaction_id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            member_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            sent_timestamp TEXT NOT NULL,
            response_type TEXT,
            response_timestamp TEXT
        );
        """
    )

    customers = [
        (
            "C00001",
            "True",
        ),
        (
            "C00002",
            "True",
        ),
        (
            "C00003",
            "True",
        ),
        (
            "C00004",
            "False",
        ),
        (
            "C00005",
            "True",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO customers (
            customer_id,
            marketing_consent
        )
        VALUES (?, ?)
        """,
        customers,
    )

    members = [
        (
            "M000001",
            "C00001",
            "ACTIVE",
            "STANDARD",
            "2025-01-01",
            None,
            1,
        ),
        (
            "M000002",
            "C00002",
            "ACTIVE",
            "PLUS",
            "2026-09-01",
            None,
            1,
        ),
        (
            "M000003",
            "C00003",
            "SUSPENDED",
            "PLUS",
            "2025-06-01",
            None,
            1,
        ),
        (
            "M000004",
            "C00004",
            "CANCELLED",
            "STANDARD",
            "2025-01-01",
            "2026-09-10",
            0,
        ),
        (
            "M000005",
            "C00005",
            "INACTIVE",
            "PLUS",
            "2025-01-01",
            "2026-08-01",
            0,
        ),
    ]

    connection.executemany(
        """
        INSERT INTO members (
            member_id,
            customer_id,
            membership_status,
            membership_tier,
            join_date,
            end_date,
            marketing_consent
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?
        )
        """,
        members,
    )

    subscriptions = [
        (
            "S0000001",
            "M000001",
            "MEMBERSHIP_STANDARD",
            "2025-01-01",
            "2026-01-31",
            "RENEWED",
            1,
            9.99,
            "EUR",
            "MONTHLY",
        ),
        (
            "S0000002",
            "M000001",
            "MEMBERSHIP_STANDARD",
            "2026-02-01",
            None,
            "RENEWED",
            1,
            9.99,
            "EUR",
            "MONTHLY",
        ),
        (
            "S0000003",
            "M000002",
            "MEMBERSHIP_PLUS",
            "2026-09-01",
            None,
            "NEW",
            1,
            19.99,
            "EUR",
            "MONTHLY",
        ),
        (
            "S0000004",
            "M000003",
            "MEMBERSHIP_PLUS",
            "2025-06-01",
            None,
            "DUE",
            1,
            19.99,
            "EUR",
            "MONTHLY",
        ),
        (
            "S0000005",
            "M000004",
            "MEMBERSHIP_STANDARD",
            "2025-01-01",
            "2026-09-10",
            "CANCELLED",
            0,
            9.99,
            "EUR",
            "MONTHLY",
        ),
        (
            "S0000006",
            "M000005",
            "MEMBERSHIP_PLUS",
            "2025-01-01",
            "2026-08-01",
            "EXPIRED",
            0,
            19.99,
            "EUR",
            "MONTHLY",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO subscriptions (
            subscription_id,
            member_id,
            plan_name,
            start_date,
            end_date,
            renewal_status,
            auto_renew,
            price,
            currency,
            billing_frequency
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        subscriptions,
    )

    membership_events = [
        (
            "ME0000001",
            "M000002",
            "UPGRADED",
            "2026-09-15T11:00:00",
        ),
        (
            "ME0000002",
            "M000003",
            "DOWNGRADED",
            "2026-09-18T11:00:00",
        ),
        (
            "ME0000003",
            "M000004",
            "CANCELLED",
            "2026-09-10T17:00:00",
        ),
        (
            "ME0000004",
            "M000001",
            "UPGRADED",
            "2026-08-01T11:00:00",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO membership_events (
            event_id,
            member_id,
            event_type,
            event_timestamp
        )
        VALUES (?, ?, ?, ?)
        """,
        membership_events,
    )

    engagement_events = [
        (
            "EE0000001",
            "M000001",
            "2026-09-05T10:00:00",
        ),
        (
            "EE0000002",
            "M000001",
            "2026-09-06T10:00:00",
        ),
        (
            "EE0000003",
            "M000002",
            "2026-08-20T10:00:00",
        ),
        (
            "EE0000004",
            "M000003",
            "2026-09-07T10:00:00",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO engagement_events (
            event_id,
            member_id,
            event_timestamp
        )
        VALUES (?, ?, ?)
        """,
        engagement_events,
    )

    benefit_redemptions = [
        (
            "BR0000001",
            "M000001",
            "REDEEMED",
            "2026-09-07T12:00:00",
        ),
        (
            "BR0000002",
            "M000001",
            "REDEEMED",
            "2026-09-08T12:00:00",
        ),
        (
            "BR0000003",
            "M000002",
            "FAILED",
            "2026-09-09T12:00:00",
        ),
        (
            "BR0000004",
            "M000003",
            "REDEEMED",
            "2026-09-10T12:00:00",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO benefit_redemptions (
            redemption_id,
            member_id,
            redemption_status,
            redemption_timestamp
        )
        VALUES (?, ?, ?, ?)
        """,
        benefit_redemptions,
    )

    campaign_interactions = [
        (
            "CI0000001",
            "MEMBER_NEWS",
            "M000001",
            "EMAIL",
            "2026-09-05T10:00:00",
            "CONVERTED",
            "2026-09-05T11:00:00",
        ),
        (
            "CI0000002",
            "MEMBER_NEWS",
            "M000002",
            "APP",
            "2026-09-06T10:00:00",
            "OPENED",
            "2026-09-06T11:00:00",
        ),
        (
            "CI0000003",
            "PLUS_UPGRADE",
            "M000004",
            "EMAIL",
            "2026-09-01T10:00:00",
            "IGNORED",
            None,
        ),
        (
            "CI0000004",
            "MEMBER_NEWS",
            "M000001",
            "EMAIL",
            "2026-08-01T10:00:00",
            "CONVERTED",
            "2026-08-01T11:00:00",
        ),
    ]

    connection.executemany(
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
            ?, ?, ?, ?, ?, ?, ?
        )
        """,
        campaign_interactions,
    )

    sql = KPI_SQL_PATH.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        sql
    )

    connection.commit()

    yield connection

    connection.close()


def dashboard(
    connection: sqlite3.Connection,
) -> sqlite3.Row:
    return connection.execute(
        """
        SELECT *
        FROM membership_kpi_dashboard
        """
    ).fetchone()


def test_reporting_window_is_defined_correctly(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert (
        row["as_of_date"]
        == "2026-09-21"
    )

    assert (
        row["window_start"]
        == "2026-08-23"
    )


def test_current_subscription_uses_latest_start_date(
    kpi_database,
):
    row = kpi_database.execute(
        """
        SELECT subscription_id
        FROM membership_current_subscriptions
        WHERE member_id = 'M000001'
        """
    ).fetchone()

    assert (
        row["subscription_id"]
        == "S0000002"
    )


def test_membership_population_kpis(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert row["total_members"] == 5
    assert row["active_members"] == 2
    assert row["new_members_30d"] == 1


def test_subscription_and_revenue_kpis(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert (
        row["active_subscriptions"]
        == 3
    )

    assert (
        row["renewed_subscriptions"]
        == 1
    )

    assert (
        row[
            "completed_renewal_outcomes"
        ]
        == 3
    )

    assert (
        row[
            "realised_renewal_rate_pct"
        ]
        == pytest.approx(
            33.33
        )
    )

    assert (
        row[
            "monthly_recurring_revenue_eur"
        ]
        == pytest.approx(
            49.97
        )
    )


def test_churn_and_retention_kpis(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert (
        row[
            "opening_membership_base_30d"
        ]
        == 3
    )

    assert (
        row[
            "churned_members_30d"
        ]
        == 1
    )

    assert (
        row[
            "churn_rate_30d_pct"
        ]
        == pytest.approx(
            33.33
        )
    )

    assert (
        row[
            "retention_rate_30d_pct"
        ]
        == pytest.approx(
            66.67
        )
    )


def test_engagement_and_benefit_kpis_are_member_level(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    #
    # M000001 has multiple events,
    # but counts once.
    #
    # M000003 is suspended and is
    # intentionally excluded.
    #
    assert (
        row[
            "engaged_active_members_30d"
        ]
        == 1
    )

    assert (
        row[
            "engagement_rate_30d_pct"
        ]
        == pytest.approx(
            50.0
        )
    )

    assert (
        row[
            "members_redeeming_benefits_30d"
        ]
        == 1
    )

    assert (
        row[
            "benefit_redemption_rate_30d_pct"
        ]
        == pytest.approx(
            50.0
        )
    )


def test_lifecycle_movement_kpis_use_reporting_window(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert (
        row["upgrades_30d"]
        == 1
    )

    assert (
        row["downgrades_30d"]
        == 1
    )


def test_campaign_conversion_kpis_use_sends_as_denominator(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    assert (
        row["campaign_sends_30d"]
        == 3
    )

    assert (
        row[
            "campaign_conversions_30d"
        ]
        == 1
    )

    assert (
        row[
            "campaign_conversion_rate_30d_pct"
        ]
        == pytest.approx(
            33.33
        )
    )


def test_consent_quality_metrics_surface_problems(
    kpi_database,
):
    row = dashboard(
        kpi_database
    )

    #
    # M000005 intentionally disagrees
    # with its authoritative customer
    # consent.
    #
    assert (
        row["consent_mismatches"]
        == 1
    )

    #
    # M000004 is an authoritative opt-out
    # but deliberately has one campaign
    # interaction in this test fixture.
    #
    assert (
        row[
            "opt_out_campaign_violations"
        ]
        == 1
    )


def test_active_tier_distribution_uses_active_members_only(
    kpi_database,
):
    rows = kpi_database.execute(
        """
        SELECT
            membership_tier,
            member_count,
            active_member_pct
        FROM membership_active_tier_distribution
        ORDER BY membership_tier
        """
    ).fetchall()

    result = {
        row["membership_tier"]: (
            row["member_count"],
            row["active_member_pct"],
        )
        for row in rows
    }

    assert result == {
        "PLUS": (
            1,
            50.0,
        ),
        "STANDARD": (
            1,
            50.0,
        ),
    }


def test_campaign_performance_excludes_sends_outside_window(
    kpi_database,
):
    rows = kpi_database.execute(
        """
        SELECT
            campaign_id,
            sends,
            converted,
            conversion_rate_pct
        FROM membership_campaign_performance_30d
        """
    ).fetchall()

    result = {
        row["campaign_id"]: {
            "sends": row["sends"],
            "converted": (
                row["converted"]
            ),
            "rate": (
                row[
                    "conversion_rate_pct"
                ]
            ),
        }
        for row in rows
    }

    assert (
        result[
            "MEMBER_NEWS"
        ]["sends"]
        == 2
    )

    assert (
        result[
            "MEMBER_NEWS"
        ]["converted"]
        == 1
    )

    assert (
        result[
            "MEMBER_NEWS"
        ]["rate"]
        == pytest.approx(
            50.0
        )
    )

    assert (
        result[
            "PLUS_UPGRADE"
        ]["sends"]
        == 1
    )

    assert (
        result[
            "PLUS_UPGRADE"
        ]["converted"]
        == 0
    )