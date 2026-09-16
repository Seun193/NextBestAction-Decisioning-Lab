# Next Best Action Decisioning Lab

A banking-style decisioning and QA engineering lab for validating customer data, business rules, APIs, decision logic, model outputs, system integrations, and release readiness.

The project demonstrates an automated quality-engineering approach to a synthetic Next Best Action platform, covering the path from customer-data ingestion through decisioning and downstream delivery.

> All customer data used in this repository is synthetic.

## Architecture Overview

The Next Best Action Decisioning Lab is structured as a testable decisioning system.

Customer data is loaded into SQLite, accessed through a repository layer, evaluated by a decision engine, and exposed through a FastAPI service.

The architecture supports rule validation, scoring, ranking, explainability, and API-level testing.

```mermaid
flowchart LR
    A[Customer Data<br/>CSV / Synthetic Dataset] --> B[Data Load Layer<br/>load_customers_to_sqlite.py]
    B --> C[(SQLite Database)]

    C --> D[Repository Layer]
    D --> E[Decision Engine]

    subgraph Decision Logic
        E1[Eligibility Rules]
        E2[Action Scoring]
        E3[Ranking & Arbitration]
        E4[Reason Codes / Explainability]
    end

    E --> E1
    E --> E2
    E --> E3
    E --> E4

    E1 --> F[FastAPI Service]
    E2 --> F
    E3 --> F
    E4 --> F

    F --> G[/health/]
    F --> H[/nba/{customer_id}/]

    I[Test Suite<br/>pytest / API tests / negative tests / reconciliation] --> F
    I --> E

    J[CI / Quality Gate] --> I
    J --> K[Release Confidence]

    H --> L[Consumers<br/>UI / API client / tester / reviewer]

## Engineering Scope

- 20,000 synthetic customer profiles
- SQLite-backed customer repository
- FastAPI decisioning API
- independent business-rule validation
- API contract and negative testing
- data-quality and pipeline validation
- database-to-API reconciliation
- full-population batch reconciliation
- upstream and downstream data-flow validation
- eligibility and constraint enforcement
- Pega-inspired candidate arbitration
- synthetic propensity-model validation
- model-to-decision integration
- GitHub Actions regression workflow
- automated fail-closed release validation
- JUnit evidence generation

## Current Validation Baseline

**101 automated tests passing**

The release-validation process includes:

- critical release-readiness smoke tests
- complete automated regression
- machine-readable JUnit evidence
- non-zero exit codes on mandatory validation failure
- explicit `PASS` or `BLOCKED` release decisions

Controlled defect experiments have also been used to verify that the automated validation can detect failures in:

- business rules
- API contracts
- upstream consent mapping
- downstream decision mapping
- eligibility enforcement
- decision constraints
- propensity-model output ranges
- model behavioural expectations
- release-readiness gates

## Focus

Banking decisioning, data validation, API testing, SQL reconciliation, decision-system validation, model-output validation, integration testing, regression automation, and release readiness.

## Technologies

- Python
- FastAPI
- SQLite
- SQL
- pytest
- Pydantic
- Git
- GitHub Actions
- CI/CD
- PowerShell

## Key Engineering Work

- Rule-based eligibility, scoring, and action ranking
- Five candidate Next Best Actions
- Reason-code generation for decision explainability
- 20,000 synthetic customer profiles
- SQLite-backed customer repository
- Database-to-API reconciliation
- Positive and negative API validation
- Data-quality and pipeline validation
- Full-population decision reconciliation
- Upstream and downstream data transformation
- Consent-integrity validation
- Pega-inspired eligibility and candidate arbitration
- Propensity-model output validation
- Model-version and feature traceability
- Automated regression testing
- GitHub Actions CI validation
- Automated release-readiness validation
- Fail-closed release gating
- JUnit evidence generation
- Controlled data-layer migration from CSV to SQLite
- Git-based baseline and feature-branch workflow

## Decisioning Architecture

- [Next Best Action Decisioning — Architecture](architecture/next-best-action-decisioning.md)

High-level flow:

```text
Synthetic customer data
        |
        v
SQLite customer repository
        |
        v
Upstream data mapping
        |
        v
Customer / consent validation
        |
        v
Eligibility and constraints
        |
        v
Propensity / decision inputs
        |
        v
Candidate arbitration and ranking
        |
        v
Next Best Action
        |
        v
Downstream decision mapping
        |
        v
FastAPI endpoint
        |
        v
Automated validation
        |
        v
Release readiness gate
```

## Next Best Action Flow

The lab evaluates customer information against multiple candidate actions.

Examples include:

- `SAVINGS_PLAN`
- `INVESTMENT_INFO`
- `MORTGAGE_CONSULTATION`
- `CREDIT_CARD_UPGRADE`
- `FINANCIAL_HEALTH_CHECK`

Each action can be evaluated using:

- eligibility
- constraints
- customer characteristics
- reason codes
- propensity
- context weighting
- business value
- business levers
- deterministic priority

The resulting candidates are ranked and a single Next Best Action is selected.

## Pega-Inspired Arbitration

The project contains a dedicated arbitration layer for validating how eligible actions compete for selection.

The simplified engineering model uses:

```text
Arbitration Score
=
Propensity
× Context Weight
× Business Value
× Business Lever
```

Eligibility and constraints remain authoritative.

A high score cannot make an ineligible or blocked action selectable.

Deterministic tie-breaking is also validated to ensure repeatable decisions.

## Propensity Model Validation

A synthetic investment-propensity model is included to demonstrate QA techniques for model-assisted decisioning.

Validation covers:

- score range between `0.0` and `1.0`
- deterministic prediction
- model-version traceability
- input-feature traceability
- savings monotonicity
- monthly-surplus monotonicity
- digital-engagement monotonicity
- invalid-input rejection
- eligibility protection
- arbitration integration

The model is intentionally synthetic and is used for testing decision-system behaviour rather than representing a production banking model.

## Data-Flow Validation

The project validates information across differently structured upstream and downstream systems.

Example upstream mapping:

```text
party_id                  -> customer_id
income_monthly_eur        -> monthly_income
savings_eur               -> savings_balance
marketing_permission      -> marketing_consent
preferred_contact_channel -> preferred_channel
```

Boolean-style values such as:

```text
Y -> True
N -> False
```

are explicitly validated.

The downstream layer also verifies that:

- the selected action is preserved
- score is preserved
- eligibility is preserved
- reason codes are preserved
- candidate ranking is preserved

This provides coverage across system boundaries rather than validating the decision engine in isolation.

## SQLite Data Layer

Synthetic customer records are loaded into a SQLite database.

The repository layer uses parameterized SQL queries to retrieve customer records before decisioning.

The database is generated locally and is not committed to the repository.

To generate the synthetic dataset:

```powershell
python -m src.synthetic_data
```

To build the SQLite database:

```powershell
python -m src.load_customers_to_sqlite
```

## API

Start the FastAPI application from the repository root:

```powershell
uvicorn src.app:app --reload
```

The local service exposes:

```text
GET /health
GET /nba/{customer_id}
```

Example valid customer identifier:

```text
C00001
```

The customer-ID contract uses:

```text
C#####
```

Malformed identifiers are rejected by API validation.

## Automated Testing

Run the complete regression suite:

```powershell
python -m pytest -q
```

Current validated baseline:

```text
101 passed
```

A known Starlette/AnyIO dependency deprecation warning may also appear. It does not currently affect test execution.

## CI Regression Validation

The repository contains a GitHub Actions workflow that automatically:

1. checks out the repository
2. configures Python
3. installs dependencies
4. generates synthetic customer data
5. builds the SQLite database
6. executes the complete pytest regression suite
7. generates JUnit evidence
8. uploads the regression artifact

The workflow runs on relevant pushes and pull requests.

This verifies that the test environment can be reproduced outside the developer's local environment.

## Release Readiness Validation

A dedicated PowerShell release-validation runner provides a two-stage automated release gate.

Run:

```powershell
.\scripts\run_release_validation.ps1
```

### Stage 1 — Release Readiness Smoke Validation

Critical cross-layer checks validate:

- API health and version
- malformed API-input rejection
- customer-identity preservation
- marketing-consent integrity
- propensity-model output contract
- model-version traceability
- arbitration eligibility protection
- downstream Next Best Action preservation
- deterministic decision behaviour

### Stage 2 — Full Regression

If the smoke gate passes, the complete automated regression suite is executed.

A healthy release produces:

```text
RELEASE RESULT: PASS
Smoke exit code      : 0
Regression exit code : 0
```

A mandatory smoke failure produces:

```text
RELEASE RESULT: BLOCKED
Exit code: 1
```

This provides fail-closed release behaviour suitable for CI/CD integration.

## Full-Population Reconciliation

The project includes sequential reconciliation of the database population against API decision results.

The verified synthetic dataset contains:

```text
20,000 customers
```

A complete reconciliation run produced:

```text
Checked:     20,000
Passed:      20,000
Failed:      0
Match rate:  100%
```

This is functional volume validation rather than concurrent load testing.

Large-scale 100K/1M-customer and concurrent traffic testing are maintained as separate performance-testing concerns.

## Validation Documentation

The project includes documented validation evidence covering the major QA layers of the NBA decisioning system:

- [SQLite Data Layer Validation](docs/validation/SQLite_Data_Layer_Validation.md)
- [Independent Business-Rule Validation](docs/validation/Business_Rule_Validation.md)
- [Data Quality and Pipeline Validation](docs/validation/Data_Quality_and_Pipeline_Validation.md)
- [API Contract and Negative Testing](docs/validation/API_Contract_and_Negative_Testing.md)
- [Batch Reconciliation Validation](docs/validation/Batch_Reconciliation_Validation.md)
- [CI Regression Workflow Validation](docs/validation/CI_Regression_Workflow_Validation.md)
- [Data-Flow Integration Validation](docs/validation/Data_Flow_Integration_Validation.md)
- [Decision Arbitration Validation](docs/validation/Decision_Arbitration_Validation.md)
- [Propensity Model Validation](docs/validation/Propensity_Model_Validation.md)
- [Release Readiness Validation](docs/validation/Release_Readiness_Validation.md)

## Requirements Documentation

Requirements used to drive independent validation are maintained under:

```text
docs/requirements/
```

They include specifications covering:

- business rules
- data quality
- API contracts
- batch reconciliation
- CI regression
- upstream/downstream data mapping
- decision arbitration
- propensity-model behaviour
- release readiness

This allows tests to be derived from documented expectations rather than simply reproducing implementation logic.

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── regression.yml
├── architecture/
├── data/
├── docs/
│   ├── requirements/
│   └── validation/
├── scripts/
│   ├── run_regression.ps1
│   └── run_release_validation.ps1
├── src/
│   ├── app.py
│   ├── arbitration.py
│   ├── batch_reconcile_db_api.py
│   ├── data_quality.py
│   ├── decision_engine.py
│   ├── downstream_adapter.py
│   ├── load_customers_to_sqlite.py
│   ├── models.py
│   ├── propensity_model.py
│   ├── reconcile_db_api.py
│   ├── repository.py
│   ├── synthetic_data.py
│   └── upstream_adapter.py
├── tests/
└── pyproject.toml
```

## Local Setup

Create and activate a Python virtual environment, then install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

Generate the synthetic customer dataset:

```powershell
python -m src.synthetic_data
```

Build the SQLite database:

```powershell
python -m src.load_customers_to_sqlite
```

Run the automated tests:

```powershell
python -m pytest -q
```

Start the API:

```powershell
uvicorn src.app:app --reload
```

Run release validation:

```powershell
.\scripts\run_release_validation.ps1
```

## Engineering Approach

The project emphasizes independent and evidence-led QA.

Validation is designed around questions such as:

- Is the source data valid?
- Was data transformed correctly between systems?
- Are business rules implemented correctly?
- Is the API contract enforced?
- Does the database agree with the API?
- Can ineligible actions ever win?
- Do model outputs remain within their defined contract?
- Does model behaviour remain consistent with expected relationships?
- Is the selected decision preserved downstream?
- Can a critical defect automatically block release?

The aim is not only to confirm that the application runs, but to determine whether the decisioning system behaves correctly across data, API, model, integration, and release boundaries.

## Repository Purpose

This repository is an independent engineering project demonstrating QA and test-automation approaches for a synthetic banking Next Best Action environment.

It contains no real customer information, proprietary banking data, or production decision logic.
