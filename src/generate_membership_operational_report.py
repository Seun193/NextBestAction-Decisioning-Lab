import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = (
    ROOT
    / "data"
    / "nba_lab.db"
)

DEFAULT_OUTPUT_PATH = (
    ROOT
    / "reports"
    / "membership"
    / "membership_operational_report.md"
)


REQUIRED_VIEWS = {
    "membership_kpi_dashboard",
    "membership_active_tier_distribution",
    "membership_campaign_performance_30d",
    "membership_recent_cohort_summary",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the Membership Data Operations "
            "business-facing operational report."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=(
            "SQLite database path. "
            f"Default: {DEFAULT_DB_PATH}"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Markdown report output path. "
            f"Default: {DEFAULT_OUTPUT_PATH}"
        ),
    )

    return parser.parse_args()


def resolve_path(
    path: Path,
) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def validate_required_views(
    connection: sqlite3.Connection,
) -> None:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'view'
        """
    ).fetchall()

    available = {
        row[0]
        for row in rows
    }

    missing = (
        REQUIRED_VIEWS
        - available
    )

    if missing:
        names = ", ".join(
            sorted(missing)
        )

        raise RuntimeError(
            "Required membership analytics "
            f"views are missing: {names}"
        )


def load_dashboard(
    connection: sqlite3.Connection,
) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT *
        FROM membership_kpi_dashboard
        """
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "membership_kpi_dashboard "
            "returned no data"
        )

    return row


def load_tier_distribution(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            membership_tier,
            member_count,
            active_member_pct
        FROM membership_active_tier_distribution
        ORDER BY
            member_count DESC,
            membership_tier
        """
    ).fetchall()


def load_campaign_performance(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            campaign_id,
            sends,
            opened,
            clicked,
            converted,
            ignored,
            conversion_rate_pct
        FROM membership_campaign_performance_30d
        ORDER BY
            conversion_rate_pct DESC,
            sends DESC,
            campaign_id
        """
    ).fetchall()


def load_recent_cohorts(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            cohort_month,
            cohort_size,
            cohort_age_months,
            month_1_retention_pct,
            month_3_retention_pct,
            month_6_retention_pct,
            month_12_retention_pct,
            latest_retention_rate_pct
        FROM membership_recent_cohort_summary
        ORDER BY cohort_month DESC
        """
    ).fetchall()


def pct(
    value,
) -> str:
    if value is None:
        return "-"

    return f"{float(value):.2f}%"


def money(
    value,
) -> str:
    return (
        f"EUR {float(value):,.2f}"
    )


def integer(
    value,
) -> str:
    return f"{int(value):,}"


def build_report(
    dashboard: sqlite3.Row,
    tiers: list[sqlite3.Row],
    campaigns: list[sqlite3.Row],
    cohorts: list[sqlite3.Row],
) -> str:
    lines = []

    lines.append(
        "# Membership Data Operations "
        "Operational Report"
    )

    lines.append("")

    lines.append(
        "> All data in this report is synthetic."
    )

    lines.append("")

    lines.append(
        f"**Reporting date:** "
        f"{dashboard['as_of_date']}"
    )

    lines.append(
        f"**30-day window:** "
        f"{dashboard['window_start']} "
        f"through {dashboard['as_of_date']}"
    )

    lines.append("")

    lines.append(
        "## Executive KPI Snapshot"
    )

    lines.append("")

    lines.append(
        "| KPI | Value |"
    )

    lines.append(
        "| --- | ---: |"
    )

    snapshot = [
        (
            "Total members",
            integer(
                dashboard[
                    "total_members"
                ]
            ),
        ),
        (
            "Active members",
            integer(
                dashboard[
                    "active_members"
                ]
            ),
        ),
        (
            "New members - 30d",
            integer(
                dashboard[
                    "new_members_30d"
                ]
            ),
        ),
        (
            "Active subscriptions",
            integer(
                dashboard[
                    "active_subscriptions"
                ]
            ),
        ),
        (
            "Realised renewal rate",
            pct(
                dashboard[
                    "realised_renewal_rate_pct"
                ]
            ),
        ),
        (
            "30-day churn rate",
            pct(
                dashboard[
                    "churn_rate_30d_pct"
                ]
            ),
        ),
        (
            "30-day retention rate",
            pct(
                dashboard[
                    "retention_rate_30d_pct"
                ]
            ),
        ),
        (
            "30-day engagement rate",
            pct(
                dashboard[
                    "engagement_rate_30d_pct"
                ]
            ),
        ),
        (
            "30-day benefit redemption rate",
            pct(
                dashboard[
                    "benefit_redemption_rate_30d_pct"
                ]
            ),
        ),
        (
            "Upgrades - 30d",
            integer(
                dashboard[
                    "upgrades_30d"
                ]
            ),
        ),
        (
            "Downgrades - 30d",
            integer(
                dashboard[
                    "downgrades_30d"
                ]
            ),
        ),
        (
            "Monthly recurring subscription value",
            money(
                dashboard[
                    "monthly_recurring_revenue_eur"
                ]
            ),
        ),
        (
            "Campaign sends - 30d",
            integer(
                dashboard[
                    "campaign_sends_30d"
                ]
            ),
        ),
        (
            "Campaign conversions - 30d",
            integer(
                dashboard[
                    "campaign_conversions_30d"
                ]
            ),
        ),
        (
            "Campaign conversion rate",
            pct(
                dashboard[
                    "campaign_conversion_rate_30d_pct"
                ]
            ),
        ),
    ]

    for label, value in snapshot:
        lines.append(
            f"| {label} | {value} |"
        )

    lines.append("")
    lines.append(
        "## Active Membership Tier Mix"
    )
    lines.append("")
    lines.append(
        "| Tier | Active members | Share |"
    )
    lines.append(
        "| --- | ---: | ---: |"
    )

    for row in tiers:
        lines.append(
            "| "
            f"{row['membership_tier']} | "
            f"{integer(row['member_count'])} | "
            f"{pct(row['active_member_pct'])} |"
        )

    lines.append("")
    lines.append(
        "## Campaign Performance - 30 Days"
    )
    lines.append("")
    lines.append(
        "| Campaign | Sends | Opened | "
        "Clicked | Converted | Ignored | "
        "Conversion |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | "
        "---: | ---: | ---: |"
    )

    for row in campaigns:
        lines.append(
            "| "
            f"{row['campaign_id']} | "
            f"{integer(row['sends'])} | "
            f"{integer(row['opened'])} | "
            f"{integer(row['clicked'])} | "
            f"{integer(row['converted'])} | "
            f"{integer(row['ignored'])} | "
            f"{pct(row['conversion_rate_pct'])} |"
        )

    lines.append("")
    lines.append(
        "## Recent Membership Cohorts"
    )
    lines.append("")
    lines.append(
        "| Cohort | Size | Age | M1 | M3 | "
        "M6 | M12 | Latest |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: |"
    )

    for row in cohorts:
        lines.append(
            "| "
            f"{row['cohort_month']} | "
            f"{integer(row['cohort_size'])} | "
            f"{integer(row['cohort_age_months'])} | "
            f"{pct(row['month_1_retention_pct'])} | "
            f"{pct(row['month_3_retention_pct'])} | "
            f"{pct(row['month_6_retention_pct'])} | "
            f"{pct(row['month_12_retention_pct'])} | "
            f"{pct(row['latest_retention_rate_pct'])} |"
        )

    lines.append("")
    lines.append(
        "## Data Quality and Compliance"
    )
    lines.append("")
    lines.append(
        "| Control | Result |"
    )
    lines.append(
        "| --- | ---: |"
    )

    lines.append(
        "| Marketing consent mismatches | "
        f"{integer(dashboard['consent_mismatches'])} |"
    )

    lines.append(
        "| Authoritative opt-out campaign violations | "
        f"{integer(dashboard['opt_out_campaign_violations'])} |"
    )

    lines.append("")
    lines.append(
        "## Operational Interpretation"
    )
    lines.append("")

    lines.append(
        "- Membership acquisition, churn, retention, "
        "engagement, benefit utilisation, revenue, "
        "campaign response, and cohort survival are "
        "reported from the same reconciled operational "
        "membership dataset."
    )

    lines.append(
        "- Campaign activity uses customer-level "
        "marketing consent as the authoritative "
        "contact-permission source."
    )

    lines.append(
        "- Consent mismatches are surfaced as "
        "data-quality exceptions rather than silently "
        "overwritten."
    )

    lines.append(
        "- Cohort milestones that have not yet become "
        "observable are shown as `-`, not as zero."
    )

    lines.append(
        "- Monthly recurring subscription value is a "
        "modeled recurring value and is not an "
        "accounting-recognised revenue measure."
    )

    lines.append("")
    lines.append(
        "## Validation"
    )
    lines.append("")

    lines.append(
        "The underlying KPI and cohort calculations "
        "are independently covered by automated "
        "pytest validation."
    )

    lines.append("")

    return "\n".join(
        lines
    )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    output_path = resolve_path(
        args.output
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: "
            f"{database_path}"
        )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.row_factory = (
            sqlite3.Row
        )

        validate_required_views(
            connection
        )

        dashboard = load_dashboard(
            connection
        )

        tiers = load_tier_distribution(
            connection
        )

        campaigns = (
            load_campaign_performance(
                connection
            )
        )

        cohorts = load_recent_cohorts(
            connection
        )

    report = build_report(
        dashboard=dashboard,
        tiers=tiers,
        campaigns=campaigns,
        cohorts=cohorts,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        report,
        encoding="utf-8",
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "MEMBERSHIP OPERATIONAL REPORT"
    )
    print("=" * 70)

    print(
        f"Reporting date      : "
        f"{dashboard['as_of_date']}"
    )

    print(
        f"Total members       : "
        f"{dashboard['total_members']:,}"
    )

    print(
        f"Active members      : "
        f"{dashboard['active_members']:,}"
    )

    print(
        f"New members - 30d   : "
        f"{dashboard['new_members_30d']:,}"
    )

    print(
        f"Campaign sends - 30d: "
        f"{dashboard['campaign_sends_30d']:,}"
    )

    print(
        f"Consent violations  : "
        f"{dashboard['opt_out_campaign_violations']:,}"
    )

    print()

    print(
        f"Output              : "
        f"{output_path}"
    )

    print()
    print("REPORT GENERATION: PASS")


if __name__ == "__main__":
    main()