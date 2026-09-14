# Next Best Action Decisioning Lab

A synthetic banking-style Next Best Action (NBA) decisioning system for exploring and validating customer-data integrity, eligibility rules, action scoring and ranking, explainability, API behaviour, and regression safety.

This project is a hands-on engineering and QA validation lab combining decisioning logic, database validation, API testing, automated regression testing, and end-to-end reconciliation.

## Focus

Banking decisioning, data validation, API testing, SQL reconciliation, and test automation.

## Technologies

Python, FastAPI, SQLite, SQL, pytest, Pydantic, Git.

## Key Engineering Work

- Rule-based eligibility, scoring, and action ranking
- Five candidate Next Best Actions
- Reason-code generation for decision explainability
- 20,000 synthetic customer profiles
- SQLite-backed customer repository
- Database-to-API reconciliation
- Positive and negative API validation
- Automated regression testing
- Controlled data-layer migration from CSV to SQLite
- Git-based baseline and feature-branch workflow

## Architecture

- [Next Best Action Decisioning — Architecture](architecture/next-best-action-decisioning.md)

High-level flow:

```text
Synthetic customer data
        |
        v
SQLite customer repository
        |
        v
Eligibility checks
        |
        v
Rule-based action scoring
        |
        v
Rank candidate actions
        |
        v
Next Best Action
        |
        v
FastAPI endpoint
        |
        v
Automated validation
```

## Validation Documentation

The project includes documented validation evidence covering the major QA layers of the NBA decisioning system:

- [SQLite Data Layer Validation](docs/validation/SQLite_Data_Layer_Validation.md)
- [Independent Business-Rule Validation](docs/validation/Business_Rule_Validation.md)
- [Data Quality and Pipeline Validation](docs/validation/Data_Quality_and_Pipeline_Validation.md)
- [API Contract and Negative Testing](docs/validation/API_Contract_and_Negative_Testing.md)
- [Batch Reconciliation Validation](docs/validation/Batch_Reconciliation_Validation.md)
- [CI Regression Workflow Validation](docs/validation/CI_Regression_Workflow_Validation.md)
- [Data-Flow Integration Validation](docs/validation/Data_Flow_Integration_Validation.md)

