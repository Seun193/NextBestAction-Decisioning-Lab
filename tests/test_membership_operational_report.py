import sqlite3

import pytest

from src.generate_membership_operational_report import (
    build_report,
    integer,
    money,
    pct,
    validate_required_views,
)


def dashboard_data():
    return {
        "as_of_date": "2026-09-21",
        "window_start": "2026-08-23",
        "total_members": 13856,
        "active_members": 11051,
        "new_members_30d": 224,
        "active_subscriptions": 11552,
        "realised_renewal_rate_pct": 75.30,
        "churn_rate_30d_pct": 0.94,
        "retention_rate_30d_pct": 99.06,
        "engagement_rate_30d_pct": 70.25,
        "benefit_redemption_rate_30d_pct": 33.17,
        "upgrades_30d": 65,
        "downgrades_30d": 0,
        "monthly_recurring_revenue_eur": 201154.48,
        "campaign_sends_30d": 4563,
        "campaign_conversions_30d": 218,
        "campaign_conversion_rate_30d_pct": 4.78,
        "consent_mismatches": 207,
        "opt_out_campaign_violations": 0,
    }


def tier_data():
    return [
        {
            "membership_tier": "STANDARD",
            "member_count": 4862,
            "active_member_pct": 44.00,
        },
        {
            "membership_tier": "PLUS",
            "member_count": 4844,
            "active_member_pct": 43.83,
        },
        {
            "membership_tier": "PREMIUM",
            "member_count": 1345,
            "active_member_pct": 12.17,
        },
    ]


def campaign_data():
    return [
        {
            "campaign_id": "MEMBER_NEWS",
            "sends": 1122,
            "opened": 415,
            "clicked": 144,
            "converted": 45,
            "ignored": 518,
            "conversion_rate_pct": 4.01,
        }
    ]


def cohort_data():
    return [
        {
            "cohort_month": "2026-09-01",
            "cohort_size": 153,
            "cohort_age_months": 0,
            "month_1_retention_pct": None,
            "month_3_retention_pct": None,
            "month_6_retention_pct": None,
            "month_12_retention_pct": None,
            "latest_retention_rate_pct": 100.00,
        },
        {
            "cohort_month": "2026-06-01",
            "cohort_size": 227,
            "cohort_age_months": 3,
            "month_1_retention_pct": 92.51,
            "month_3_retention_pct": 84.14,
            "month_6_retention_pct": None,
            "month_12_retention_pct": None,
            "latest_retention_rate_pct": 84.14,
        },
    ]


def make_report():
    return build_report(
        dashboard=dashboard_data(),
        tiers=tier_data(),
        campaigns=campaign_data(),
        cohorts=cohort_data(),
    )


def test_number_formatters():
    assert integer(13856) == "13,856"
    assert pct(75.3) == "75.30%"
    assert pct(None) == "-"
    assert money(201154.48) == "EUR 201,154.48"


def test_report_contains_reporting_context():
    report = make_report()

    assert (
        "# Membership Data Operations Operational Report"
        in report
    )

    assert (
        "> All data in this report is synthetic."
        in report
    )

    assert (
        "**Reporting date:** 2026-09-21"
        in report
    )

    assert (
        "**30-day window:** "
        "2026-08-23 through 2026-09-21"
        in report
    )


def test_report_contains_expected_kpi_values():
    report = make_report()

    assert (
        "| Total members | 13,856 |"
        in report
    )

    assert (
        "| Active members | 11,051 |"
        in report
    )

    assert (
        "| New members - 30d | 224 |"
        in report
    )

    assert (
        "| Monthly recurring subscription value "
        "| EUR 201,154.48 |"
        in report
    )

    assert (
        "| Campaign conversion rate | 4.78% |"
        in report
    )


def test_report_contains_all_operational_sections():
    report = make_report()

    required_sections = [
        "## Executive KPI Snapshot",
        "## Active Membership Tier Mix",
        "## Campaign Performance - 30 Days",
        "## Recent Membership Cohorts",
        "## Data Quality and Compliance",
        "## Operational Interpretation",
        "## Validation",
    ]

    for section in required_sections:
        assert section in report


def test_immature_cohort_displays_unavailable_milestones_as_dash():
    report = make_report()

    assert (
        "| 2026-09-01 | 153 | 0 | "
        "- | - | - | - | 100.00% |"
        in report
    )


def test_report_surfaces_data_quality_controls():
    report = make_report()

    assert (
        "| Marketing consent mismatches | 207 |"
        in report
    )

    assert (
        "| Authoritative opt-out campaign violations "
        "| 0 |"
        in report
    )


def test_report_output_is_ascii_safe():
    report = make_report()

    assert "€" not in report
    assert "—" not in report
    assert "â€" not in report
    assert "â‚¬" not in report

    assert "EUR 201,154.48" in report


def test_missing_required_views_are_rejected():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        connection.execute(
            """
            CREATE VIEW membership_kpi_dashboard
            AS
            SELECT 1 AS value
            """
        )

        with pytest.raises(
            RuntimeError,
            match=(
                "Required membership analytics "
                "views are missing"
            ),
        ):
            validate_required_views(
                connection
            )

    finally:
        connection.close()


def test_required_views_pass_validation():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        connection.executescript(
            """
            CREATE VIEW membership_kpi_dashboard
            AS
            SELECT 1 AS value;

            CREATE VIEW membership_active_tier_distribution
            AS
            SELECT 1 AS value;

            CREATE VIEW membership_campaign_performance_30d
            AS
            SELECT 1 AS value;

            CREATE VIEW membership_recent_cohort_summary
            AS
            SELECT 1 AS value;
            """
        )

        validate_required_views(
            connection
        )

    finally:
        connection.close()