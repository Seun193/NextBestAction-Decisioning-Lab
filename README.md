# Next Best Action Decisioning Lab

A synthetic banking-style decisioning system for exploring and validating customer-data integrity, eligibility rules, action scoring and ranking, explainability, API behaviour, and regression safety.

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

## Case Study

- [Validating a Data-Layer Migration in a Next Best Action Decisioning System](case-studies/nba-data-layer-migration-validation.md)

## Validation Focus

The lab is designed around three main validation concerns:

### Data Integrity

Is the correct customer record being consumed by the decisioning system?

### Decision Integrity

Are eligibility, score, ranking, winning action, and reason codes consistent with the customer input?

### Regression Safety

Can infrastructure or data-layer changes occur without changing established decision behaviour?

## Repository

- [NextBestAction-Decisioning-Lab](https://github.com/Seun193/NextBestAction-Decisioning-Lab)

## Related Research

- [FinlandPowerMarketLab-Showcase](https://github.com/Seun193/FinlandPowerMarketLab-Showcase)
