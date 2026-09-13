# NBA Business Rules v1

## Purpose

This document defines the expected eligibility and ranking behaviour of the rule-based Next Best Action engine.

These requirements act as the independent test oracle for automated QA validation.

## Savings Plan

### BR-SAV-001

`SAVINGS_PLAN` is eligible only when:

- `marketing_consent = true`

If marketing consent is false:

- action must be ineligible
- score must be `0`
- reason codes must include `NO_MARKETING_CONSENT`

## Investment Information

### BR-INV-001

`INVESTMENT_INFO` is eligible only when all of the following are true:

- `marketing_consent = true`
- `investment_consent = true`
- `age >= 18`

If investment consent is false:

- action must be ineligible
- score must be `0`
- reason codes must include `NO_INVESTMENT_CONSENT`

## Mortgage Consultation

### BR-MORT-001

`MORTGAGE_CONSULTATION` is eligible only when:

- `marketing_consent = true`
- customer does not already have a mortgage
- `age >= 23`

If the customer already has a mortgage:

- action must be ineligible
- score must be `0`
- reason codes must include `ALREADY_HAS_MORTGAGE`

## Credit Card Upgrade

### BR-CC-001

`CREDIT_CARD_UPGRADE` is eligible only when:

- `marketing_consent = true`
- customer already has a credit card
- `credit_score_band != LOW`

If the customer does not have a credit card:

- action must be ineligible
- score must be `0`
- reason codes must include `NO_EXISTING_CREDIT_CARD`

If the credit-score band is LOW:

- action must be ineligible
- score must be `0`
- reason codes must include `LOW_CREDIT_SCORE_BAND`

## Financial Health Check

### BR-FHC-001

`FINANCIAL_HEALTH_CHECK` must always remain eligible.

Marketing consent is not required because this is treated as a customer-support action rather than a marketing action.

## Ranking

### BR-RANK-001

Eligible actions must rank ahead of ineligible actions.

### BR-RANK-002

Within the same eligibility state, actions must be ordered by score from highest to lowest.

## Winner Selection

### BR-WIN-001

The Next Best Action must be the highest-ranked eligible action.