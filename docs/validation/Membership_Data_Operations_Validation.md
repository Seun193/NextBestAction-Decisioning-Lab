# Membership Data Operations Validation

## Purpose

This document records validation evidence for the synthetic Membership Data Operations capability integrated with the Next Best Action Decisioning Lab.

The capability covers membership ingestion, subscriptions, lifecycle activity, engagement, benefits, campaigns, SQL analytics, operational reporting, and membership-aware decisioning.

All data used by the project is synthetic.

---

## Requirements Basis

Validation is derived from:

docs/requirements/Membership_Data_Operations_Requirements_v1.md

The requirements cover member identity, subscriptions, lifecycle events, engagement, benefit use, campaign activity, consent integrity, reconciliation, data quality, KPIs, cohorts, operational reporting, NBA integration, regression protection, and synthetic-data controls.

---

## Data Model

The membership capability extends the existing customers table with:

- members
- subscriptions
- membership_events
- engagement_events
- benefit_redemptions
- campaign_interactions

The principal relationship is:

customers.customer_id -> members.customer_id

Membership-domain event tables reference:

members.member_id

---

## Validated Synthetic Population

The validated dataset contains:

| Entity | Rows |
| --- | ---: |
| Customers | 20,000 |
| Members | 13,856 |
| Subscriptions | 15,559 |
| Membership events | 42,169 |
| Engagement events | 79,791 |
| Benefit redemptions | 32,379 |
| Campaign interactions | 24,248 |

Membership status distribution:

| Status | Members |
| --- | ---: |
| ACTIVE | 11,051 |
| CANCELLED | 1,223 |
| INACTIVE | 1,081 |
| SUSPENDED | 501 |

Membership tier distribution:

| Tier | Members |
| --- | ---: |
| STANDARD | 6,162 |
| PLUS | 6,031 |
| PREMIUM | 1,663 |

---

## Referential Integrity

Validated relationships include:

- members.customer_id -> customers.customer_id
- subscriptions.member_id -> members.member_id
- membership_events.member_id -> members.member_id
- engagement_events.member_id -> members.member_id
- benefit_redemptions.member_id -> members.member_id
- campaign_interactions.member_id -> members.member_id

Validated result:

Foreign-key violations: 0

---

## Source-to-Database Reconciliation

Membership ingestion validates:

- source rows
- inserted rows
- rejected rows
- duplicate handling
- database row counts
- reload safety
- referential integrity

The controls are designed to detect silent record loss and unintended duplication.

Generated membership CSV files and SQLite databases are excluded from version control.

---

## Lifecycle Validation

Membership lifecycle history is represented through membership_events.

Supported events include:

- JOINED
- RENEWED
- UPGRADED
- DOWNGRADED
- SUSPENDED
- REACTIVATED
- CANCELLED

Validated results include:

| Metric | Result |
| --- | ---: |
| Total lifecycle events | 42,169 |
| Joined in trailing 30 days | 224 |
| Total upgrade events | 1,703 |
| Upgrades in trailing 30 days | 65 |

The latest generated upgrade was observed on 2026-09-20.

The current synthetic population contains no downgrade events. This is treated as a generator characteristic rather than evidence that the event type is unsupported.

---

## Engagement and Benefit Validation

The validated population contains:

- 79,791 engagement events
- 32,379 benefit redemption records

Successful benefit utilisation requires:

redemption_status = REDEEMED

Failed and reversed redemptions are excluded from successful-redemption metrics.

Trailing-window calculations use the configured reporting date and exclude future activity.

---

## Campaign Validation

The validated population contains 24,248 campaign interactions.

Response distribution:

| Response | Count |
| --- | ---: |
| CLICKED | 3,422 |
| CONVERTED | 1,206 |
| IGNORED | 10,763 |
| OPENED | 8,857 |

Validation covers:

- valid member relationships
- supported response types
- send timestamps
- response timestamps
- campaign conversions
- latest observable response
- future-event exclusion

---

## Marketing Consent Integrity

Customer-system marketing consent remains authoritative.

Membership-system consent cannot override the banking customer consent value.

Validated results:

| Metric | Result |
| --- | ---: |
| Customer marketing consent = true | 11,648 |
| Suppressed by customer authority | 2,208 |
| Consent mismatches | 207 |
| Opt-out campaign violations | 0 |

Consent mismatches are surfaced as data-quality exceptions rather than silently corrected.

---

## Membership KPI Layer

KPI definitions are documented in:

docs/kpi_definitions.md

SQL implementation:

sql/membership_kpis.sql

Reporting snapshot:

2026-09-21

Inclusive trailing 30-day period:

2026-08-23 through 2026-09-21

Validated results include:

| KPI | Result |
| --- | ---: |
| Total members | 13,856 |
| Active members | 11,051 |
| New members - 30 days | 224 |
| Active subscriptions | 11,552 |
| Renewed subscriptions | 7,023 |
| Completed renewal outcomes | 9,327 |
| Realised renewal rate | 75.30% |
| Churn rate - 30 days | 0.94% |
| Retention rate - 30 days | 99.06% |
| Engagement rate - 30 days | 70.25% |
| Benefit redemption rate - 30 days | 33.17% |
| Upgrades - 30 days | 65 |
| Downgrades - 30 days | 0 |
| Monthly recurring revenue | EUR 201,154.48 |
| Campaign sends - 30 days | 4,563 |
| Campaign conversions - 30 days | 218 |
| Campaign conversion rate | 4.78% |
| Consent mismatches | 207 |
| Opt-out campaign violations | 0 |

Monthly recurring revenue is a modeled analytical KPI and is not accounting or cash-receipt data.

---

## Cohort Retention Analytics

Cohort implementation:

sql/membership_cohorts.sql

Membership cohorts are based on calendar month of join date.

Month 0 represents the original cohort population at 100%.

Example validated 2025-09 cohort:

| Month | Retained | Rate |
| --- | ---: | ---: |
| M0 | 233 | 100.00% |
| M1 | 228 | 97.85% |
| M3 | 224 | 96.14% |
| M6 | 212 | 90.99% |
| M9 | 202 | 86.70% |
| M12 | 187 | 80.26% |

Automated tests validate:

- future-cohort exclusion
- Month-0 population
- monthly retention curves
- checkpoint handling
- current-month capping
- immature milestones
- mature milestones
- recent cohort summaries
- monotonic retention
- cohort ranking

---

## Operational Reporting

Report generator:

src/generate_membership_operational_report.py

Generated reports are written beneath:

reports/membership/

The operational report includes:

- membership KPIs
- subscription performance
- retention
- engagement
- benefit utilisation
- campaign performance
- recurring revenue
- cohort results
- data-quality exceptions

Generated reports are intentionally excluded from Git.

---

## Membership Decisioning Context

Membership information is supplied to decisioning through MembershipContext.

The context contains:

- member_id
- membership_status
- membership_tier
- tenure_days
- engagement_events_30d
- successful_benefit_redemptions_30d
- campaign_sends_30d
- campaign_conversions_30d
- latest_campaign_response

Customer marketing and investment consent remain authoritative in the banking Customer model.

---

## Repository Context Validation

The repository derives MembershipContext directly from SQLite.

Independent correlated subqueries are used for engagement, benefits, and campaign activity to avoid row multiplication across one-to-many event tables.

Automated validation covers:

- member lookup
- status and tier
- tenure calculation
- inclusive 30-day window
- engagement counts
- successful benefit counts
- campaign sends
- campaign conversions
- latest observable campaign response
- non-member behaviour
- future-event exclusion

---

## Optional Membership Schema Safety

The original banking API must continue to work where membership tables are unavailable.

Before membership SQL runs, the repository checks for:

- members
- engagement_events
- benefit_redemptions
- campaign_interactions

If the required schema is absent:

get_membership_context(...)

returns None.

This preserves compatibility with the customer-only CI database and environments that have not installed membership data.

An automated regression test protects this behaviour.

---

## Membership-Aware Decision Ranking

Membership ranking logic is implemented in:

src/membership_decisioning.py

The original banking decision engine remains responsible for eligibility.

Membership signals may refine relevance only after eligibility is established.

Current synthetic relevance adjustments include:

| Signal | Adjustment |
| --- | ---: |
| Recent membership engagement | +0.03 |
| Recent campaign conversion | +0.04 |
| Recent campaign click | +0.02 |
| Recent campaign open | +0.01 |

Membership context cannot:

- create eligibility
- override marketing consent
- override investment consent
- override existing product rules
- make an ineligible action selectable

Membership tier, tenure, and benefit utilisation are not used as proxies for financial suitability.

These adjustments are synthetic lab policies and do not represent production banking rules.

---

## Non-Member Compatibility

When no membership record exists:

MembershipContext = None

The membership-aware layer preserves the original NBA result.

Automated validation verifies that:

decide_with_membership(customer, None)

produces the same result as:

decide(customer)

---

## API Integration

The API decision path is:

GET /nba/{customer_id}
        |
        v
get_customer(customer_id)
        |
        v
get_membership_context(customer_id)
        |
        v
MembershipContext or None
        |
        v
decide_with_membership(...)
        |
        v
NBAResponse

The public NBAResponse contract remains unchanged.

---

## Real Database API Smoke Validation

A post-integration smoke test was executed against actual generated SQLite records.

Member path:

| Field | Result |
| --- | --- |
| Customer | C00005 |
| Membership status | ACTIVE |
| Membership tier | STANDARD |
| Engagement events - 30d | 2 |
| Campaign conversions - 30d | 0 |
| HTTP status | 200 |
| Next Best Action | FINANCIAL_HEALTH_CHECK |
| Score | 0.36 |
| Reason | LOW_EMERGENCY_SAVINGS |

The member did not meet the membership relevance thresholds, so the underlying banking recommendation remained authoritative.

Non-member path:

| Field | Result |
| --- | --- |
| Customer | C00001 |
| Membership context | None |
| HTTP status | 200 |
| Next Best Action | SAVINGS_PLAN |
| Score | 0.52 |

Result:

REAL DATABASE API SMOKE TEST: PASS

---

## Regression Baseline

Pre-membership baseline:

101 automated tests

Current validated baseline:

317 automated tests passing

The expanded suite demonstrates that the original banking regression scope remains protected while membership validation has been added.

---

## Release Validation

Release validation command:

.\scripts\run_release_validation.ps1

Stage 1:

8 passed
Smoke exit code: 0

Stage 2:

317 passed
Regression exit code: 0

Final result:

RELEASE RESULT: PASS

JUnit evidence is generated beneath:

reports/release/

Generated release evidence is not committed to the repository.

---

## Known Dependency Warning

The suite reports one dependency warning from Starlette TestClient / AnyIO:

The anyio.abc.BlockingPortal alias is deprecated.

The warning does not currently cause test failure and remains visible rather than being suppressed.

---

## CI Validation

GitHub Actions regression validation remained green throughout the membership implementation checkpoints.

The workflow:

- installs dependencies
- generates synthetic customer data
- builds the customer SQLite database
- runs the complete pytest suite
- generates JUnit evidence
- uploads the regression report

Membership-specific tests create isolated fixtures where required.

Optional membership-schema handling preserves compatibility with the customer-only CI environment.

---

## Requirement Coverage Summary

The implementation provides evidence for:

- MDO-001 Member identity
- MDO-002 Customer-to-member relationship
- MDO-003 Membership status
- MDO-004 Membership tier
- MDO-005 Membership dates
- MDO-006 Subscription identity
- MDO-007 Subscription period
- MDO-008 Renewal status
- MDO-009 Subscription commercial data
- MDO-010 Membership lifecycle history
- MDO-011 Engagement events
- MDO-012 Benefit redemptions
- MDO-013 Benefit eligibility validation
- MDO-014 Campaign interactions
- MDO-015 Marketing consent integrity
- MDO-016 Duplicate detection
- MDO-017 Referential integrity
- MDO-018 Source-to-database reconciliation
- MDO-019 Data-quality reporting
- MDO-020 Membership operational KPIs
- MDO-021 Cohort analysis
- MDO-022 SQL analytics
- MDO-023 Operational reporting
- MDO-024 Next Best Action integration
- MDO-025 Existing regression protection
- MDO-026 Synthetic data only

---

## Validation Conclusion

The membership capability has been validated across:

Synthetic data
-> ingestion
-> SQLite
-> data quality
-> lifecycle and engagement
-> benefits and campaigns
-> KPI and cohort analytics
-> operational reporting
-> membership decisioning context
-> membership-aware ranking
-> FastAPI integration
-> real-database smoke validation
-> automated regression
-> release validation

Final validated baseline:

317 passed
RELEASE RESULT: PASS

The current synthetic Membership Data Operations scope therefore preserves the original banking decisioning controls while adding independently validated membership-data and analytical capabilities.
