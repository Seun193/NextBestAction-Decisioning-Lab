-- ============================================================
-- Membership Data Operations KPI Layer
-- Next Best Action Decisioning Lab
--
-- Reporting date : 2026-09-21
-- 30-day window   : 2026-08-23 through 2026-09-21
-- ============================================================


-- ------------------------------------------------------------
-- 1. REPORTING PARAMETERS
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_reporting_parameters;

CREATE VIEW membership_reporting_parameters AS
SELECT
    DATE('2026-09-21') AS as_of_date,
    DATE('2026-09-21', '-29 days') AS window_start;


-- ------------------------------------------------------------
-- 2. CURRENT SUBSCRIPTION PER MEMBER
--
-- Demonstrates:
--   - CTE
--   - window function
--   - ranking
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_current_subscriptions;

CREATE VIEW membership_current_subscriptions AS
WITH ranked_subscriptions AS (
    SELECT
        s.*,

        ROW_NUMBER() OVER (
            PARTITION BY s.member_id
            ORDER BY
                DATE(s.start_date) DESC,
                s.subscription_id DESC
        ) AS subscription_rank

    FROM subscriptions AS s
)

SELECT
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

FROM ranked_subscriptions

WHERE subscription_rank = 1;


-- ------------------------------------------------------------
-- 3. ACTIVE MEMBER TIER DISTRIBUTION
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_active_tier_distribution;

CREATE VIEW membership_active_tier_distribution AS
WITH active_base AS (
    SELECT
        COUNT(*) AS active_members
    FROM members
    WHERE membership_status = 'ACTIVE'
)

SELECT
    m.membership_tier,

    COUNT(*) AS member_count,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(
            (
                SELECT active_members
                FROM active_base
            ),
            0
        ),
        2
    ) AS active_member_pct

FROM members AS m

WHERE m.membership_status = 'ACTIVE'

GROUP BY
    m.membership_tier

ORDER BY
    member_count DESC,
    m.membership_tier;


-- ------------------------------------------------------------
-- 4. CAMPAIGN PERFORMANCE BY CAMPAIGN
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_campaign_performance_30d;

CREATE VIEW membership_campaign_performance_30d AS
WITH params AS (
    SELECT
        as_of_date,
        window_start
    FROM membership_reporting_parameters
)

SELECT
    ci.campaign_id,

    COUNT(*) AS sends,

    SUM(
        CASE
            WHEN ci.response_type = 'OPENED'
            THEN 1
            ELSE 0
        END
    ) AS opened,

    SUM(
        CASE
            WHEN ci.response_type = 'CLICKED'
            THEN 1
            ELSE 0
        END
    ) AS clicked,

    SUM(
        CASE
            WHEN ci.response_type = 'CONVERTED'
            THEN 1
            ELSE 0
        END
    ) AS converted,

    SUM(
        CASE
            WHEN ci.response_type = 'IGNORED'
            THEN 1
            ELSE 0
        END
    ) AS ignored,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN ci.response_type = 'CONVERTED'
                THEN 1
                ELSE 0
            END
        )
        / NULLIF(
            COUNT(*),
            0
        ),
        2
    ) AS conversion_rate_pct

FROM campaign_interactions AS ci
CROSS JOIN params

WHERE DATE(ci.sent_timestamp)
      BETWEEN params.window_start
          AND params.as_of_date

GROUP BY
    ci.campaign_id

ORDER BY
    conversion_rate_pct DESC,
    sends DESC,
    ci.campaign_id;


-- ------------------------------------------------------------
-- 5. MAIN KPI DASHBOARD
-- ------------------------------------------------------------

DROP VIEW IF EXISTS membership_kpi_dashboard;

CREATE VIEW membership_kpi_dashboard AS
WITH

params AS (
    SELECT
        as_of_date,
        window_start
    FROM membership_reporting_parameters
),


-- ------------------------------------------------------------
-- Membership population
-- ------------------------------------------------------------

member_metrics AS (
    SELECT
        COUNT(*) AS total_members,

        SUM(
            CASE
                WHEN membership_status = 'ACTIVE'
                THEN 1
                ELSE 0
            END
        ) AS active_members,

        SUM(
            CASE
                WHEN DATE(join_date)
                     BETWEEN params.window_start
                         AND params.as_of_date
                THEN 1
                ELSE 0
            END
        ) AS new_members_30d

    FROM members
    CROSS JOIN params
),


-- ------------------------------------------------------------
-- Current subscription state
-- ------------------------------------------------------------

subscription_metrics AS (
    SELECT
        SUM(
            CASE
                WHEN end_date IS NULL
                 AND renewal_status IN (
                    'NEW',
                    'RENEWED',
                    'DUE'
                 )
                THEN 1
                ELSE 0
            END
        ) AS active_subscriptions,

        SUM(
            CASE
                WHEN renewal_status = 'RENEWED'
                THEN 1
                ELSE 0
            END
        ) AS renewed_subscriptions,

        SUM(
            CASE
                WHEN renewal_status IN (
                    'RENEWED',
                    'CANCELLED',
                    'EXPIRED'
                )
                THEN 1
                ELSE 0
            END
        ) AS completed_renewal_outcomes,

        ROUND(
            SUM(
                CASE
                    WHEN end_date IS NULL
                     AND renewal_status IN (
                        'NEW',
                        'RENEWED',
                        'DUE'
                     )
                     AND currency = 'EUR'
                     AND billing_frequency = 'MONTHLY'
                    THEN price
                    ELSE 0
                END
            ),
            2
        ) AS monthly_recurring_revenue_eur

    FROM membership_current_subscriptions
),


-- ------------------------------------------------------------
-- Opening membership population
-- ------------------------------------------------------------

opening_base AS (
    SELECT
        COUNT(*) AS opening_membership_base_30d

    FROM members
    CROSS JOIN params

    WHERE DATE(join_date) <= params.window_start

      AND (
            end_date IS NULL
            OR DATE(end_date)
               >= params.window_start
      )
),


-- ------------------------------------------------------------
-- Churn
-- ------------------------------------------------------------

churn_metrics AS (
    SELECT
        COUNT(
            DISTINCT me.member_id
        ) AS churned_members_30d

    FROM membership_events AS me
    CROSS JOIN params

    WHERE me.event_type = 'CANCELLED'

      AND DATE(me.event_timestamp)
          BETWEEN params.window_start
              AND params.as_of_date
),


-- ------------------------------------------------------------
-- Engagement
-- ------------------------------------------------------------

engagement_metrics AS (
    SELECT
        COUNT(
            DISTINCT ee.member_id
        ) AS engaged_active_members_30d

    FROM engagement_events AS ee

    JOIN members AS m
      ON m.member_id = ee.member_id

    CROSS JOIN params

    WHERE m.membership_status = 'ACTIVE'

      AND DATE(ee.event_timestamp)
          BETWEEN params.window_start
              AND params.as_of_date
),


-- ------------------------------------------------------------
-- Benefit redemption
-- ------------------------------------------------------------

benefit_metrics AS (
    SELECT
        COUNT(
            DISTINCT br.member_id
        ) AS members_redeeming_benefits_30d

    FROM benefit_redemptions AS br

    JOIN members AS m
      ON m.member_id = br.member_id

    CROSS JOIN params

    WHERE m.membership_status = 'ACTIVE'

      AND br.redemption_status = 'REDEEMED'

      AND DATE(br.redemption_timestamp)
          BETWEEN params.window_start
              AND params.as_of_date
),


-- ------------------------------------------------------------
-- Lifecycle movements
-- ------------------------------------------------------------

lifecycle_metrics AS (
    SELECT
        SUM(
            CASE
                WHEN me.event_type = 'UPGRADED'
                THEN 1
                ELSE 0
            END
        ) AS upgrades_30d,

        SUM(
            CASE
                WHEN me.event_type = 'DOWNGRADED'
                THEN 1
                ELSE 0
            END
        ) AS downgrades_30d

    FROM membership_events AS me
    CROSS JOIN params

    WHERE DATE(me.event_timestamp)
          BETWEEN params.window_start
              AND params.as_of_date
),


-- ------------------------------------------------------------
-- Campaign metrics
-- ------------------------------------------------------------

campaign_metrics AS (
    SELECT
        COUNT(*) AS campaign_sends_30d,

        SUM(
            CASE
                WHEN ci.response_type = 'CONVERTED'
                THEN 1
                ELSE 0
            END
        ) AS campaign_conversions_30d

    FROM campaign_interactions AS ci
    CROSS JOIN params

    WHERE DATE(ci.sent_timestamp)
          BETWEEN params.window_start
              AND params.as_of_date
),


-- ------------------------------------------------------------
-- Consent reconciliation
-- ------------------------------------------------------------

consent_metrics AS (
    SELECT
        SUM(
            CASE
                WHEN
                    CASE
                        WHEN LOWER(
                            CAST(
                                m.marketing_consent AS TEXT
                            )
                        ) IN (
                            '1',
                            'true'
                        )
                        THEN 1
                        ELSE 0
                    END
                    !=
                    CASE
                        WHEN LOWER(
                            CAST(
                                c.marketing_consent AS TEXT
                            )
                        ) IN (
                            '1',
                            'true'
                        )
                        THEN 1
                        ELSE 0
                    END
                THEN 1
                ELSE 0
            END
        ) AS consent_mismatches

    FROM members AS m

    JOIN customers AS c
      ON c.customer_id = m.customer_id
),


-- ------------------------------------------------------------
-- Campaign compliance
-- ------------------------------------------------------------

campaign_compliance AS (
    SELECT
        COUNT(*) AS opt_out_campaign_violations

    FROM campaign_interactions AS ci

    JOIN members AS m
      ON m.member_id = ci.member_id

    JOIN customers AS c
      ON c.customer_id = m.customer_id

    WHERE LOWER(
        CAST(
            c.marketing_consent AS TEXT
        )
    ) IN (
        '0',
        'false'
    )
)


SELECT
    params.as_of_date,
    params.window_start,

    member_metrics.total_members,
    member_metrics.active_members,
    member_metrics.new_members_30d,

    subscription_metrics.active_subscriptions,

    subscription_metrics.renewed_subscriptions,

    subscription_metrics.completed_renewal_outcomes,

    ROUND(
        100.0
        * subscription_metrics.renewed_subscriptions
        / NULLIF(
            subscription_metrics.completed_renewal_outcomes,
            0
        ),
        2
    ) AS realised_renewal_rate_pct,

    opening_base.opening_membership_base_30d,

    churn_metrics.churned_members_30d,

    ROUND(
        100.0
        * churn_metrics.churned_members_30d
        / NULLIF(
            opening_base.opening_membership_base_30d,
            0
        ),
        2
    ) AS churn_rate_30d_pct,

    ROUND(
        100.0
        * (
            opening_base.opening_membership_base_30d
            - churn_metrics.churned_members_30d
        )
        / NULLIF(
            opening_base.opening_membership_base_30d,
            0
        ),
        2
    ) AS retention_rate_30d_pct,

    engagement_metrics.engaged_active_members_30d,

    ROUND(
        100.0
        * engagement_metrics.engaged_active_members_30d
        / NULLIF(
            member_metrics.active_members,
            0
        ),
        2
    ) AS engagement_rate_30d_pct,

    benefit_metrics.members_redeeming_benefits_30d,

    ROUND(
        100.0
        * benefit_metrics.members_redeeming_benefits_30d
        / NULLIF(
            member_metrics.active_members,
            0
        ),
        2
    ) AS benefit_redemption_rate_30d_pct,

    lifecycle_metrics.upgrades_30d,
    lifecycle_metrics.downgrades_30d,

    subscription_metrics.monthly_recurring_revenue_eur,

    campaign_metrics.campaign_sends_30d,
    campaign_metrics.campaign_conversions_30d,

    ROUND(
        100.0
        * campaign_metrics.campaign_conversions_30d
        / NULLIF(
            campaign_metrics.campaign_sends_30d,
            0
        ),
        2
    ) AS campaign_conversion_rate_30d_pct,

    consent_metrics.consent_mismatches,

    campaign_compliance.opt_out_campaign_violations

FROM params

CROSS JOIN member_metrics
CROSS JOIN subscription_metrics
CROSS JOIN opening_base
CROSS JOIN churn_metrics
CROSS JOIN engagement_metrics
CROSS JOIN benefit_metrics
CROSS JOIN lifecycle_metrics
CROSS JOIN campaign_metrics
CROSS JOIN consent_metrics
CROSS JOIN campaign_compliance;