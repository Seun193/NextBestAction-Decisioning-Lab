# Validating a Data-Layer Migration in a Next Best Action Decisioning System

## Context

I maintain a synthetic banking-style Next Best Action (NBA) decisioning environment for exploring decision-system validation, data integrity, API behaviour, eligibility, ranking, explainability, and regression risk.

The system contains 20,000 synthetic customer profiles and evaluates five candidate actions before selecting the highest-ranked eligible action.

The implementation itself remains private. This case study documents the engineering and QA approach.

---

## Problem

The original customer repository loaded customer records directly from a CSV file.

The data-access layer was migrated to SQLite to introduce a more realistic persistence layer and allow SQL-based validation.

The key requirement was:

> The storage implementation may change, but established customer decisions must remain unchanged.

---

## Risk

A data-layer migration can introduce defects even when the decision logic itself is untouched.

Potential failure modes included:

- incorrect field mapping
- numeric type changes
- boolean conversion errors
- missing or duplicated records
- incorrect customer lookup
- unexpected null handling
- changed eligibility outcomes
- altered action scores
- changed action ranking
- incorrect reason codes

A successful application startup or HTTP `200` response would therefore not be sufficient evidence of correctness.

---

## Architecture

```mermaid
flowchart LR
    A[Synthetic Customer Data] --> B[SQLite]
    B --> C[Repository Layer]
    C --> D[Eligibility Rules]
    D --> E[Action Scoring]
    E --> F[Ranking & Arbitration]
    F --> G[Next Best Action]
    G --> H[FastAPI]

    B --> I[QA Reconciliation]
    H --> I
    I --> J[Regression Validation]
