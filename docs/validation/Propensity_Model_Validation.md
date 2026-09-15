# Propensity Model Validation

## Objective

Validate the synthetic propensity-scoring layer used by the NBA Decisioning Lab.

The model estimates customer propensity for an investment-related Next Best Action and supplies that score to the arbitration layer.

The implementation is designed for QA and decision-system validation and does not represent a production banking model.

---

## Decision Flow

```text
Customer Features
        ↓
Propensity Model
        ↓
Propensity Score
        ↓
Eligibility / Constraints
        ↓
Arbitration
        ↓
Next Best Action