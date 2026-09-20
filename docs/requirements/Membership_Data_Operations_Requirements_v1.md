# Membership Data Operations Requirements v1

## Purpose

Define the data-management, quality, reconciliation, and analytical requirements for a synthetic membership operations capability integrated with the Next Best Action Decisioning Lab.

The membership layer is intended to demonstrate:

- membership data management
- subscription operations
- engagement analysis
- benefit usage
- data-quality controls
- source-to-database reconciliation
- SQL analytics
- operational reporting
- integration with Next Best Action decisioning

All data is synthetic.

---

## Scope

The membership data model shall extend the existing customer environment.

Existing entity:

`customers`

New entities:

- `members`
- `subscriptions`
- `membership_events`
- `engagement_events`
- `benefit_redemptions`
- `campaign_interactions`

The existing `customer_id` shall be the link between customer and membership data.

---

## MDO-001 — Member Identity

Every membership record shall have a unique:

`member_id`

Format:

`M######`

Example:

`M000001`

A member shall reference an existing customer through:

`customer_id`

---

## MDO-002 — Customer-to-Member Relationship

Every `members.customer_id` shall exist in the existing `customers` table.

Orphan membership records shall be treated as data-quality failures.

The initial model shall allow no more than one primary membership record per customer.

---

## MDO-003 — Membership Status

Supported membership statuses shall be:

- `ACTIVE`
- `INACTIVE`
- `SUSPENDED`
- `CANCELLED`

Any other value shall fail validation.

---

## MDO-004 — Membership Tier

Supported membership tiers shall initially be:

- `STANDARD`
- `PLUS`
- `PREMIUM`

Any unsupported tier shall fail validation.

---

## MDO-005 — Membership Dates

Each member shall contain:

- `join_date`
- optional `end_date`

Rules:

- `join_date` is mandatory
- `end_date`, when present, shall not precede `join_date`
- active memberships shall normally have no membership end date
- cancelled or inactive memberships may contain an end date

---

## MDO-006 — Subscription Identity

Every subscription shall have a unique:

`subscription_id`

Each subscription shall reference an existing `member_id`.

Orphan subscription records shall fail validation.

---

## MDO-007 — Subscription Period

Each subscription shall contain:

- `start_date`
- optional `end_date`

Rules:

- `start_date` is mandatory
- `end_date`, when present, shall not precede `start_date`
- overlapping active subscription periods for the same member shall be detected
- subscription history shall remain preserved

---

## MDO-008 — Renewal Status

Supported renewal states shall initially be:

- `NEW`
- `RENEWED`
- `DUE`
- `CANCELLED`
- `EXPIRED`

`auto_renew` shall be stored as a boolean-style value.

Invalid renewal states shall fail validation.

---

## MDO-009 — Subscription Commercial Data

Each subscription may contain:

- plan name
- subscription price
- currency
- billing frequency
- auto-renew status

Negative subscription prices shall not be permitted.

Initial supported currency:

`EUR`

---

## MDO-010 — Membership Event History

Membership lifecycle changes shall be represented in:

`membership_events`

Supported initial event types:

- `JOINED`
- `RENEWED`
- `UPGRADED`
- `DOWNGRADED`
- `SUSPENDED`
- `REACTIVATED`
- `CANCELLED`

Every event shall reference an existing member.

---

## MDO-011 — Engagement Events

Member engagement shall be represented through:

`engagement_events`

Examples include:

- app session
- content view
- email open
- campaign click
- event registration
- benefit view

Each engagement event shall contain:

- event identifier
- member identifier
- event type
- event timestamp
- channel

---

## MDO-012 — Benefit Redemptions

Member benefit use shall be recorded in:

`benefit_redemptions`

Each redemption shall contain:

- redemption identifier
- member identifier
- benefit code
- redemption timestamp
- redemption status
- optional monetary value

Supported redemption statuses:

- `REDEEMED`
- `REVERSED`
- `FAILED`

---

## MDO-013 — Membership Eligibility for Benefits

A successful benefit redemption shall reference a member whose membership was active at the time of redemption.

Invalid redemption relationships shall be detectable through data-quality validation.

---

## MDO-014 — Campaign Interactions

Membership campaign activity shall be stored in:

`campaign_interactions`

Each record may contain:

- campaign identifier
- member identifier
- channel
- sent timestamp
- response type
- response timestamp

Supported initial response types:

- `OPENED`
- `CLICKED`
- `CONVERTED`
- `IGNORED`

---

## MDO-015 — Marketing Consent Integrity

Membership marketing activity shall respect the customer's existing marketing-consent value.

Where membership-system consent and customer-system consent disagree, the discrepancy shall be surfaced as a data-quality exception.

The customer source shall remain authoritative unless explicitly changed by a later requirement.

---

## MDO-016 — Duplicate Detection

The validation layer shall detect:

- duplicate `member_id`
- duplicate `subscription_id`
- multiple primary memberships for one customer
- suspicious duplicated member records
- duplicate source events where applicable

Duplicate detection shall not silently delete records.

Potential duplicates shall be reported for investigation.

---

## MDO-017 — Referential Integrity

The following relationships shall be validated:

`members.customer_id -> customers.customer_id`

`subscriptions.member_id -> members.member_id`

`membership_events.member_id -> members.member_id`

`engagement_events.member_id -> members.member_id`

`benefit_redemptions.member_id -> members.member_id`

`campaign_interactions.member_id -> members.member_id`

Orphan records shall be reported.

---

## MDO-018 — Source-to-Database Reconciliation

Membership ingestion shall report:

- source rows
- inserted rows
- rejected rows
- duplicate rows
- database rows

The reconciliation shall provide enough information to prove that no source records disappeared silently.

---

## MDO-019 — Data Quality Reporting

The system shall produce counts for at least:

- duplicate members
- orphan members
- invalid membership statuses
- invalid tiers
- invalid subscription dates
- overlapping subscriptions
- invalid renewal states
- consent mismatches
- orphan engagement events
- invalid benefit redemptions

---

## MDO-020 — Membership Operational KPIs

The analytics layer shall support calculation of:

- total members
- active members
- new members
- active subscriptions
- renewal rate
- churn rate
- retention rate
- 30-day engagement rate
- benefit-redemption rate
- tier distribution
- upgrades and downgrades
- subscription revenue
- campaign conversion rate

KPI definitions shall be documented before implementation.

---

## MDO-021 — Cohort Analysis

The analytics layer shall support membership cohorts based on join month.

The system shall be capable of calculating retained-member counts and retention rates for subsequent periods.

---

## MDO-022 — SQL Analytics

Operational analytics shall demonstrate SQL techniques including:

- joins
- aggregations
- common table expressions
- window functions
- conditional logic
- ranking
- date-based grouping

The SQL layer shall remain independently verifiable.

---

## MDO-023 — Operational Reporting

Membership results shall eventually be exportable into a business-facing operational report containing:

- executive summary
- membership KPIs
- subscription growth
- retention cohorts
- engagement
- benefit usage
- campaign performance
- data-quality exceptions

---

## MDO-024 — Next Best Action Integration

Membership attributes may later contribute to candidate actions such as:

- `MEMBERSHIP_RENEWAL`
- `MEMBERSHIP_UPGRADE`
- `BENEFIT_REMINDER`
- `ENGAGEMENT_CAMPAIGN`
- `MEMBERSHIP_REACTIVATION`

Eligibility and consent rules shall remain authoritative.

Membership integration shall not bypass existing decision-system controls.

---

## MDO-025 — Existing Regression Protection

Membership implementation shall not break the existing Next Best Action regression baseline.

Before membership functionality is merged:

`101 existing tests`

shall continue to pass unless the baseline is intentionally expanded.

---

## MDO-026 — Synthetic Data Only

The membership environment shall contain synthetic data only.

No real customer, subscriber, payment, campaign, or membership information shall be committed to the repository.

---

## Validation Strategy

Membership validation shall eventually cover:

1. schema validation
2. referential integrity
3. business-rule validation
4. duplicate detection
5. source-to-database reconciliation
6. SQL KPI verification
7. cohort-analysis verification
8. API/decision integration
9. regression protection
10. volume testing