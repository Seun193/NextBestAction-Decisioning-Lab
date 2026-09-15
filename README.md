# Next Best Action Decisioning Lab

A banking-style decisioning and QA engineering lab for validating customer data, business rules, APIs, decision logic, model outputs, system integrations, and release readiness.

The project demonstrates an automated quality-engineering approach to a synthetic Next Best Action platform, covering the path from customer data ingestion through decisioning and downstream delivery.

## Engineering Scope

- 20,000 synthetic customer profiles
- SQLite-backed customer repository
- FastAPI decisioning API
- independent business-rule validation
- API contract and negative testing
- data-quality validation
- database-to-API reconciliation
- full-population batch reconciliation
- upstream and downstream mapping validation
- eligibility and constraint enforcement
- Pega-inspired candidate arbitration
- synthetic propensity-model validation
- GitHub Actions regression workflow
- automated fail-closed release validation
- JUnit evidence generation

## Current Validation Baseline

**101 automated tests passing**

Release validation includes:

- critical release-readiness smoke tests
- full automated regression
- machine-readable JUnit evidence
- non-zero exit code on mandatory validation failure
- explicit `PASS` or `BLOCKED` release decisions

