# Decision Arbitration Validation

## Objective

Validate candidate-action arbitration for the NBA Decisioning Lab.

The validation covers the decision process used to resolve competition between multiple candidate actions after considering eligibility, delivery constraints, propensity, context weighting, business value, business levers, and deterministic priority.

---

## Arbitration Flow

The implemented decision flow is:

```text
Candidate Actions
        ↓
Eligibility Gate
        ↓
Constraint Gate
        ↓
Propensity
        ↓
Context Weight
        ↓
Business Value
        ↓
Business Lever
        ↓
Arbitration Score
        ↓
Priority / Tie-Breaking
        ↓
Winning Next Best Action