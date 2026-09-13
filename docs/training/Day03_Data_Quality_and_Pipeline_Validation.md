# Day 3 — Data Quality and Pipeline Validation

## Objective

Validate customer data before it reaches the Next Best Action decision engine.

The goal was to detect malformed, incomplete, duplicate, or invalid customer records early enough that they cannot influence NBA eligibility, scoring, ranking, or API responses.

---

## Pipeline Position

Day 3 introduced a data-quality gate before decisioning:

```text
Raw customer data
        ↓
Data Quality Validation
        ↓
SQLite repository
        ↓
Customer model
        ↓
NBA decision engine
        ↓
FastAPI