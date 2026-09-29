import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

COHORT_SQL_PATH = (
    ROOT
    / "sql"
    / "membership_cohorts.sql"
)


@pytest.fixture
def cohort_database(
    tmp_path: Path,
):
    database_path = (
        tmp_path
        / "membership_cohort_test.db"
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE members (
            member_id TEXT PRIMARY KEY,
            join_date TEXT NOT NULL,
            end_date TEXT
        );
        """
    )

    members = [
        # --------------------------------------------------
        # 2026-01 cohort
        #
        # Month 0 : 4 / 4
        # Month 1 : 3 / 4
        # Month 2 : 2 / 4
        # Month 3 : 1 / 4
        # --------------------------------------------------
        (
            "M000001",
            "2026-01-05",
            None,
        ),
        (
            "M000002",
            "2026-01-10",
            "2026-01-20",
        ),
        (
            "M000003",
            "2026-01-15",
            "2026-02-28",
        ),
        (
            "M000004",
            "2026-01-20",
            "2026-04-15",
        ),

        # --------------------------------------------------
        # 2026-06 cohort
        #
        # Used to test ranking.
        # Both members survive through Month 3.
        # --------------------------------------------------
        (
            "M000005",
            "2026-06-03",
            None,
        ),
        (
            "M000006",
            "2026-06-15",
            None,
        ),

        # --------------------------------------------------
        # 2026-08 cohort
        #
        # Month 1 checkpoint is capped at 2026-09-21.
        #
        # M000007 survives.
        # M000008 ends before the checkpoint.
        # M000009 ends exactly on the checkpoint and counts.
        # --------------------------------------------------
        (
            "M000007",
            "2026-08-05",
            None,
        ),
        (
            "M000008",
            "2026-08-20",
            "2026-09-10",
        ),
        (
            "M000009",
            "2026-08-25",
            "2026-09-21",
        ),

        # --------------------------------------------------
        # 2026-09 cohort
        #
        # Age 0. No future milestones should exist.
        # --------------------------------------------------
        (
            "M000010",
            "2026-09-02",
            None,
        ),
        (
            "M000011",
            "2026-09-10",
            "2026-09-15",
        ),

        # --------------------------------------------------
        # Future member must not enter an observable cohort.
        # --------------------------------------------------
        (
            "M000012",
            "2026-10-01",
            None,
        ),
    ]

    connection.executemany(
        """
        INSERT INTO members (
            member_id,
            join_date,
            end_date
        )
        VALUES (?, ?, ?)
        """,
        members,
    )

    sql = COHORT_SQL_PATH.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        sql
    )

    connection.commit()

    yield connection

    connection.close()


def test_future_members_are_excluded(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT COUNT(*) AS count
        FROM membership_cohort_retention
        WHERE cohort_month = '2026-10-01'
        """
    ).fetchone()

    assert row["count"] == 0


def test_month_zero_equals_original_cohort_size(
    cohort_database,
):
    rows = cohort_database.execute(
        """
        SELECT
            cohort_size,
            retained_members,
            retention_rate_pct
        FROM membership_cohort_retention
        WHERE month_number = 0
        """
    ).fetchall()

    assert rows

    for row in rows:
        assert (
            row["retained_members"]
            == row["cohort_size"]
        )

        assert (
            row["retention_rate_pct"]
            == pytest.approx(
                100.0
            )
        )


def test_january_cohort_retention_curve(
    cohort_database,
):
    rows = cohort_database.execute(
        """
        SELECT
            month_number,
            retained_members,
            retention_rate_pct
        FROM membership_cohort_retention
        WHERE cohort_month = '2026-01-01'
          AND month_number BETWEEN 0 AND 3
        ORDER BY month_number
        """
    ).fetchall()

    result = [
        (
            row["month_number"],
            row["retained_members"],
            row["retention_rate_pct"],
        )
        for row in rows
    ]

    assert result == [
        (
            0,
            4,
            100.0,
        ),
        (
            1,
            3,
            75.0,
        ),
        (
            2,
            2,
            50.0,
        ),
        (
            3,
            1,
            25.0,
        ),
    ]


def test_member_ending_exactly_on_checkpoint_is_retained(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT
            checkpoint_date,
            retained_members,
            retention_rate_pct
        FROM membership_cohort_retention
        WHERE cohort_month = '2026-08-01'
          AND month_number = 1
        """
    ).fetchone()

    assert (
        row["checkpoint_date"]
        == "2026-09-21"
    )

    assert (
        row["retained_members"]
        == 2
    )

    assert (
        row["retention_rate_pct"]
        == pytest.approx(
            66.67
        )
    )


def test_current_incomplete_month_is_capped_at_as_of_date(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT
            checkpoint_date
        FROM membership_cohort_retention
        WHERE cohort_month = '2026-08-01'
          AND month_number = 1
        """
    ).fetchone()

    assert (
        row["checkpoint_date"]
        == "2026-09-21"
    )


def test_immature_cohort_has_null_future_milestones(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT
            cohort_age_months,
            month_1_retention_pct,
            month_3_retention_pct,
            month_6_retention_pct,
            month_12_retention_pct
        FROM membership_cohort_milestones
        WHERE cohort_month = '2026-09-01'
        """
    ).fetchone()

    assert (
        row["cohort_age_months"]
        == 0
    )

    assert (
        row["month_1_retention_pct"]
        is None
    )

    assert (
        row["month_3_retention_pct"]
        is None
    )

    assert (
        row["month_6_retention_pct"]
        is None
    )

    assert (
        row["month_12_retention_pct"]
        is None
    )


def test_mature_cohort_milestones_are_correct(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT
            month_1_retention_pct,
            month_3_retention_pct,
            month_6_retention_pct
        FROM membership_cohort_milestones
        WHERE cohort_month = '2026-01-01'
        """
    ).fetchone()

    assert (
        row["month_1_retention_pct"]
        == pytest.approx(
            75.0
        )
    )

    assert (
        row["month_3_retention_pct"]
        == pytest.approx(
            25.0
        )
    )

    assert (
        row["month_6_retention_pct"]
        == pytest.approx(
            25.0
        )
    )


def test_latest_summary_uses_latest_observable_month(
    cohort_database,
):
    row = cohort_database.execute(
        """
        SELECT
            cohort_age_months,
            latest_observable_month,
            latest_checkpoint_date
        FROM membership_cohort_summary
        WHERE cohort_month = '2026-01-01'
        """
    ).fetchone()

    assert (
        row["cohort_age_months"]
        == 8
    )

    assert (
        row["latest_observable_month"]
        == 8
    )

    assert (
        row["latest_checkpoint_date"]
        == "2026-09-21"
    )


def test_retention_never_increases_with_cohort_age(
    cohort_database,
):
    cohort_months = [
        row["cohort_month"]
        for row in cohort_database.execute(
            """
            SELECT DISTINCT cohort_month
            FROM membership_cohort_retention
            ORDER BY cohort_month
            """
        ).fetchall()
    ]

    for cohort_month in cohort_months:
        rows = cohort_database.execute(
            """
            SELECT retained_members
            FROM membership_cohort_retention
            WHERE cohort_month = ?
            ORDER BY month_number
            """,
            (
                cohort_month,
            ),
        ).fetchall()

        retained = [
            row["retained_members"]
            for row in rows
        ]

        assert retained == sorted(
            retained,
            reverse=True,
        )


def test_month_three_ranking_orders_cohorts_by_retention(
    cohort_database,
):
    rows = cohort_database.execute(
        """
        SELECT
            cohort_month,
            month_3_retention_pct,
            month_3_retention_rank
        FROM membership_cohort_rankings
        WHERE cohort_month IN (
            '2026-01-01',
            '2026-06-01'
        )
        ORDER BY month_3_retention_rank
        """
    ).fetchall()

    assert len(rows) == 2

    assert (
        rows[0]["cohort_month"]
        == "2026-06-01"
    )

    assert (
        rows[0]["month_3_retention_pct"]
        == pytest.approx(
            100.0
        )
    )

    assert (
        rows[1]["cohort_month"]
        == "2026-01-01"
    )

    assert (
        rows[1]["month_3_retention_pct"]
        == pytest.approx(
            25.0
        )
    )