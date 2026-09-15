# NBA Propensity Model Rules v1

## Purpose

This specification defines validation requirements for a synthetic propensity model used by the NBA Decisioning Lab.

The model estimates customer propensity for an investment-related action.

The implementation is designed for QA and decision-system validation and does not represent a production banking model.

---

## PM-001 — Score Range

Every propensity prediction shall be between `0.0` and `1.0`.

---

## PM-002 — Deterministic Prediction

Identical input features and the same model version shall produce the same propensity score.

---

## PM-003 — Model Version Traceability

Every prediction shall expose the model version used to generate the score.

---

## PM-004 — Feature Traceability

The prediction result shall expose the feature values used during scoring.

---

## PM-005 — Savings Monotonicity

Holding other test inputs constant, a materially higher savings balance shall not reduce investment propensity.

---

## PM-006 — Surplus Monotonicity

Holding other test inputs constant, a materially higher monthly surplus shall not reduce investment propensity.

---

## PM-007 — Engagement Monotonicity

Holding other test inputs constant, increased digital engagement shall not reduce investment propensity.

---

## PM-008 — Invalid Input Rejection

Invalid financial or activity inputs shall be rejected before model scoring.

Examples include:

- monthly income less than or equal to zero
- negative savings balance
- negative application-visit count

---

## PM-009 — Propensity Does Not Override Eligibility

A high propensity score shall not make an otherwise ineligible action selectable.

Eligibility and constraint rules remain authoritative.

---

## PM-010 — Decision Integration

A valid propensity prediction may be supplied to the arbitration layer as an action's propensity input.

The resulting arbitration decision shall remain consistent with eligibility, constraints, business value, context weighting, and business levers.