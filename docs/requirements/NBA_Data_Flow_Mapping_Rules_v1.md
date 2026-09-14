# NBA Data-Flow Mapping Rules v1

## Purpose

This specification defines the validation rules for transforming synthetic upstream banking customer data into the internal customer representation used by the NBA decision engine.

The purpose is to verify that data crossing the upstream-to-decisioning boundary is mapped accurately, completely, and without changing its business meaning.

---

## Upstream Customer Record

The simulated upstream source provides the following fields:

| Upstream field | Meaning |
|---|---|
| party_id | Unique customer identifier |
| age_years | Customer age in years |
| income_monthly_eur | Monthly customer income in euros |
| savings_eur | Customer savings balance in euros |
| surplus_monthly_eur | Monthly disposable surplus in euros |
| mortgage_flag | Mortgage ownership represented as Y/N |
| credit_card_flag | Credit-card ownership represented as Y/N |
| investment_customer_flag | Existing investment-customer status represented as Y/N |
| app_visits_30d | Number of application visits during the previous 30 days |
| marketing_permission | General marketing consent represented as Y/N |
| investment_permission | Investment-related consent represented as Y/N |
| credit_score_band | Synthetic credit-score category |
| preferred_contact_channel | Customer's preferred communication channel |

---

## Mapping Requirements

### DF-MAP-001 — Customer Identifier

`party_id` shall map directly to `customer_id`.

No truncation, formatting, or substitution is permitted.

### DF-MAP-002 — Age

`age_years` shall map directly to `age`.

### DF-MAP-003 — Monthly Income

`income_monthly_eur` shall map directly to `monthly_income`.

The numeric value shall not change during transformation.

### DF-MAP-004 — Savings Balance

`savings_eur` shall map directly to `savings_balance`.

### DF-MAP-005 — Monthly Surplus

`surplus_monthly_eur` shall map directly to `monthly_surplus`.

### DF-MAP-006 — Boolean Flag Conversion

The following upstream fields use Y/N representation:

- `mortgage_flag`
- `credit_card_flag`
- `investment_customer_flag`
- `marketing_permission`
- `investment_permission`

The mapping shall be:

- `Y` → `True`
- `N` → `False`

No other value is valid.

### DF-MAP-007 — Application Activity

`app_visits_30d` shall map directly to `app_visits_30d`.

### DF-MAP-008 — Credit Score Band

`credit_score_band` shall map directly to `credit_score_band`.

### DF-MAP-009 — Preferred Channel

`preferred_contact_channel` shall map directly to `preferred_channel`.

### DF-MAP-010 — Completeness

Every required upstream field shall be present before a record can be transformed into the internal customer model.

### DF-MAP-011 — Invalid Flag Rejection

Boolean-style upstream fields containing values other than `Y` or `N` shall be rejected.

Examples of invalid values include:

- `YES`
- `NO`
- `1`
- `0`
- blank values

### DF-MAP-012 — Business Meaning Preservation

Transformation shall not alter the business meaning of any customer attribute.

For example:

`marketing_permission = "N"`

must never result in:

`marketing_consent = True`

because this could make a customer eligible for an action that should not be delivered.