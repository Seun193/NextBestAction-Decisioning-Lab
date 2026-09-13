# Independent NBA Business-Rule Validation

## Objective

Validate the Next Best Action decision engine against independently documented business requirements.

The purpose is to avoid using the production decision logic itself as the only source of expected results.

The database-to-API validation established integration consistency.

This validation establishes requirement compliance.

---

## Starting Point

The NBA Decisioning Lab already contained:

- SQLite-backed customer data
- Five candidate NBA actions
- Eligibility rules
- Scoring and ranking
- Reason codes
- FastAPI endpoints
- Database-to-API reconciliation
- Automated regression tests

The existing test suite already contained some eligibility checks, but the business requirements were not yet formally documented and traceable to test cases.

---

## Independent Test Oracle

An important QA concept used in this validation is the independent test oracle.

The database-to-API reconciliation effectively tested:

```text
Database
   ↓
decision_engine.py
   ↓
API

Expected == Actual