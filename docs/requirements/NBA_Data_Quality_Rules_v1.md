# NBA Data Quality Rules v1

## Purpose

These rules define the minimum data-quality requirements that customer
records must satisfy before entering the Next Best Action decisioning
pipeline.

The rules are based on the current synthetic-customer source contract.

## Rules

### DQ-001 — Required Fields

All required customer fields must be present and non-empty.

### DQ-002 — Customer ID Format

`customer_id` must follow:

`C#####`

Example:

`C00001`

### DQ-003 — Customer ID Uniqueness

Every customer ID must be unique within the dataset.

### DQ-004 — Age

Age must be an integer between:

`18` and `75`

### DQ-005 — Monthly Income

Monthly income must be between:

`900` and `14000`

### DQ-006 — Savings Balance

Savings balance must be between:

`0` and `250000`

### DQ-007 — Monthly Surplus

Monthly surplus must be between:

`-1500` and `5000`

### DQ-008 — App Visits

`app_visits_30d` must be an integer between:

`0` and `50`

### DQ-009 — Boolean Fields

The following fields must contain valid boolean values:

- has_mortgage
- has_credit_card
- investment_customer
- marketing_consent
- investment_consent

### DQ-010 — Credit Score Band

Allowed values:

- LOW
- MEDIUM
- HIGH

### DQ-011 — Preferred Channel

Allowed values:

- MOBILE
- WEB
- BRANCH
- PHONE