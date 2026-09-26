-- ============================================================
-- Membership Cohort Retention Analysis
-- Next Best Action Decisioning Lab
--
-- Reporting date : 2026-09-21
--
-- Cohort definition:
--   Calendar month in which a member joined.
--
-- Retention definition:
--   Month 0 = original cohort size, therefore 100%.
--
--   For month N > 0, a member is retained when the membership
--   has not ended before the end-of-month checkpoint for that
--   cohort month.
--
--   For the current incomplete month, the checkpoint is capped
--   at the reporting as-of date.
--
--   ACTIVE and SUSPENDED memberships are therefore retained
--   when they have no end date. Retention measures membership
--   survival, not current ACTIVE status.
-- ============================================================


-- ------------------------------------------------------------
-- 1. COHORT RETENTION CURVE
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_cohort_rankings;
DROP VIEW IF EXISTS membership_recent_cohort_summary;
DROP VIEW IF EXISTS membership_cohort_milestones;
DROP VIEW IF EXISTS membership_cohort_summary;
DROP VIEW IF EXISTS membership_cohort_retention;


CREATE VIEW membership_cohort_retention AS

WITH RECURSIVE

params AS (
    SELECT
        DATE('2026-09-21') AS as_of_date
),


-- ------------------------------------------------------------
-- Assign each member to a calendar-month cohort.
-- ------------------------------------------------------------

cohort_members AS (
    SELECT
        m.member_id,

        DATE(
            m.join_date
        ) AS join_date,

        CASE
            WHEN m.end_date IS NULL
              OR TRIM(m.end_date) = ''
            THEN NULL

            ELSE DATE(
                m.end_date
            )
        END AS end_date,

        DATE(
            m.join_date,
            'start of month'
        ) AS cohort_month

    FROM members AS m

    CROSS JOIN params

    WHERE DATE(
        m.join_date
    ) <= params.as_of_date
),


-- ------------------------------------------------------------
-- Original cohort population.
-- ------------------------------------------------------------

cohort_sizes AS (
    SELECT
        cohort_month,

        COUNT(*) AS cohort_size

    FROM cohort_members

    GROUP BY
        cohort_month
),


-- ------------------------------------------------------------
-- Calculate how many calendar months are observable for each
-- cohort as of the reporting date.
-- ------------------------------------------------------------

cohort_ages AS (
    SELECT
        cs.cohort_month,
        cs.cohort_size,
        params.as_of_date,

        (
            (
                CAST(
                    STRFTIME(
                        '%Y',
                        params.as_of_date
                    )
                    AS INTEGER
                )
                -
                CAST(
                    STRFTIME(
                        '%Y',
                        cs.cohort_month
                    )
                    AS INTEGER
                )
            ) * 12
            +
            (
                CAST(
                    STRFTIME(
                        '%m',
                        params.as_of_date
                    )
                    AS INTEGER
                )
                -
                CAST(
                    STRFTIME(
                        '%m',
                        cs.cohort_month
                    )
                    AS INTEGER
                )
            )
        ) AS cohort_age_months

    FROM cohort_sizes AS cs

    CROSS JOIN params
),


-- ------------------------------------------------------------
-- Produce month 0 through the latest observable month for
-- every cohort.
-- ------------------------------------------------------------

month_grid AS (
    SELECT
        cohort_month,
        cohort_size,
        as_of_date,
        cohort_age_months,

        0 AS month_number

    FROM cohort_ages

    UNION ALL

    SELECT
        cohort_month,
        cohort_size,
        as_of_date,
        cohort_age_months,

        month_number + 1

    FROM month_grid

    WHERE month_number
          < cohort_age_months
),


-- ------------------------------------------------------------
-- Month-end checkpoint.
--
-- Current incomplete month is capped at as_of_date.
-- ------------------------------------------------------------

checkpoints AS (
    SELECT
        cohort_month,
        cohort_size,
        cohort_age_months,
        month_number,

        MIN(
            DATE(
                cohort_month,
                PRINTF(
                    '+%d months',
                    month_number
                ),
                '+1 month',
                '-1 day'
            ),
            as_of_date
        ) AS checkpoint_date

    FROM month_grid
),


-- ------------------------------------------------------------
-- Count retained members.
--
-- Month 0 is defined as the original cohort population.
-- Subsequent months evaluate membership survival at the
-- month-end checkpoint.
-- ------------------------------------------------------------

retention_counts AS (
    SELECT
        c.cohort_month,
        c.cohort_size,
        c.cohort_age_months,
        c.month_number,
        c.checkpoint_date,

        CASE
            WHEN c.month_number = 0
            THEN c.cohort_size

            ELSE SUM(
                CASE
                    WHEN cm.join_date
                         <= c.checkpoint_date

                     AND (
                            cm.end_date IS NULL
                            OR cm.end_date
                               >= c.checkpoint_date
                         )

                    THEN 1
                    ELSE 0
                END
            )
        END AS retained_members

    FROM checkpoints AS c

    JOIN cohort_members AS cm
      ON cm.cohort_month
         = c.cohort_month

    GROUP BY
        c.cohort_month,
        c.cohort_size,
        c.cohort_age_months,
        c.month_number,
        c.checkpoint_date
)


SELECT
    cohort_month,
    cohort_size,
    cohort_age_months,
    month_number,
    checkpoint_date,
    retained_members,

    ROUND(
        100.0
        * retained_members
        / NULLIF(
            cohort_size,
            0
        ),
        2
    ) AS retention_rate_pct

FROM retention_counts;


-- ------------------------------------------------------------
-- 2. LATEST OBSERVABLE RETENTION BY COHORT
-- ------------------------------------------------------------

CREATE VIEW membership_cohort_summary AS

WITH ranked AS (
    SELECT
        cohort_month,
        cohort_size,
        cohort_age_months,
        month_number,
        checkpoint_date,
        retained_members,
        retention_rate_pct,

        ROW_NUMBER() OVER (
            PARTITION BY cohort_month

            ORDER BY
                month_number DESC
        ) AS latest_rank

    FROM membership_cohort_retention
)

SELECT
    cohort_month,
    cohort_size,
    cohort_age_months,

    month_number
        AS latest_observable_month,

    checkpoint_date
        AS latest_checkpoint_date,

    retained_members
        AS latest_retained_members,

    retention_rate_pct
        AS latest_retention_rate_pct

FROM ranked

WHERE latest_rank = 1;


-- ------------------------------------------------------------
-- 3. STANDARD RETENTION MILESTONES
--
-- NULL means the cohort is not yet mature enough for the
-- requested milestone.
-- ------------------------------------------------------------

CREATE VIEW membership_cohort_milestones AS

SELECT
    r.cohort_month,
    MAX(
        r.cohort_size
    ) AS cohort_size,

    MAX(
        r.cohort_age_months
    ) AS cohort_age_months,

    MAX(
        CASE
            WHEN r.month_number = 1
            THEN r.retention_rate_pct
        END
    ) AS month_1_retention_pct,

    MAX(
        CASE
            WHEN r.month_number = 3
            THEN r.retention_rate_pct
        END
    ) AS month_3_retention_pct,

    MAX(
        CASE
            WHEN r.month_number = 6
            THEN r.retention_rate_pct
        END
    ) AS month_6_retention_pct,

    MAX(
        CASE
            WHEN r.month_number = 12
            THEN r.retention_rate_pct
        END
    ) AS month_12_retention_pct,

    s.latest_observable_month,

    s.latest_retained_members,

    s.latest_retention_rate_pct

FROM membership_cohort_retention AS r

JOIN membership_cohort_summary AS s
  ON s.cohort_month
     = r.cohort_month

GROUP BY
    r.cohort_month,
    s.latest_observable_month,
    s.latest_retained_members,
    s.latest_retention_rate_pct;


-- ------------------------------------------------------------
-- 4. RECENT 12-MONTH COHORT SUMMARY
-- ------------------------------------------------------------

CREATE VIEW membership_recent_cohort_summary AS

SELECT
    cohort_month,
    cohort_size,
    cohort_age_months,
    month_1_retention_pct,
    month_3_retention_pct,
    month_6_retention_pct,
    month_12_retention_pct,
    latest_observable_month,
    latest_retained_members,
    latest_retention_rate_pct

FROM membership_cohort_milestones

WHERE cohort_month
      >= DATE(
            '2026-09-21',
            'start of month',
            '-11 months'
         )

ORDER BY
    cohort_month DESC;


-- ------------------------------------------------------------
-- 5. THREE-MONTH RETENTION RANKING
--
-- Only cohorts mature enough to have a complete month-3
-- checkpoint participate.
-- ------------------------------------------------------------

CREATE VIEW membership_cohort_rankings AS

SELECT
    cohort_month,
    cohort_size,
    cohort_age_months,
    month_3_retention_pct,

    RANK() OVER (
        ORDER BY
            month_3_retention_pct DESC,
            cohort_month DESC
    ) AS month_3_retention_rank

FROM membership_cohort_milestones

WHERE cohort_age_months >= 3
  AND month_3_retention_pct IS NOT NULL;