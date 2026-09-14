# NBA Arbitration Rules v1

## Purpose

This specification defines the validation rules for candidate-action arbitration in the NBA Decisioning Lab.

The implementation models enterprise decisioning concepts including eligibility, constraints, propensity, context weighting, business value, and business levers.

---

## Arbitration Flow

Candidate actions are evaluated in the following order:

1. Eligibility
2. Constraints
3. Propensity
4. Context weighting
5. Business value
6. Business lever
7. Arbitration score
8. Winner selection

---

## ARB-001 — Eligibility Gate

An action with `eligible = false` shall not be selected as the winning Next Best Action regardless of its calculated score.

---

## ARB-002 — Constraint Gate

An action with `constraint_passed = false` shall not be selected as the winning Next Best Action.

Constraints may represent contact-policy restrictions, channel restrictions, suppression rules, or other delivery limitations.

---

## ARB-003 — Propensity Range

Propensity shall be between `0.0` and `1.0`.

Propensity represents the estimated likelihood that the action is relevant or accepted.

---

## ARB-004 — Context Weight

Context weight shall be non-negative.

It represents the importance of an action in the current interaction context.

---

## ARB-005 — Business Value

Business value shall be non-negative.

It represents the relative commercial or strategic value associated with the action.

---

## ARB-006 — Business Lever

Business lever shall be non-negative.

A lever may temporarily increase or decrease the relative priority of an action.

---

## ARB-007 — Arbitration Score

For each candidate:

`arbitration_score = propensity × context_weight × business_value × business_lever`

---

## ARB-008 — Winner Selection

Among actions that pass both eligibility and constraints, the candidate with the highest arbitration score shall be selected.

---

## ARB-009 — Deterministic Tie-Breaking

If two eligible candidates have the same arbitration score, the configured numeric priority shall determine the winner.

A lower numeric priority value represents higher priority.

If score and priority are identical, action code shall provide deterministic ordering.

---

## ARB-010 — No Eligible Winner

If no candidate passes both eligibility and constraints, the arbitration result shall contain no winning action.

---

## ARB-011 — Ranking Transparency

The result shall preserve the evaluated candidates and expose:

- action code
- arbitration score
- eligibility
- constraint status
- propensity
- context weight
- business value
- business lever
- priority

This allows QA validation of why an action won or lost.