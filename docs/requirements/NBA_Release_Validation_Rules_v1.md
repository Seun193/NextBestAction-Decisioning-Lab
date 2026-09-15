# NBA Release Validation Rules v1

## Purpose

This specification defines the minimum validation gates required before an NBA Decisioning Lab release candidate can be considered ready for release.

A release shall be blocked if any mandatory gate fails.

---

## RV-001 — API Health

The API health endpoint shall return HTTP 200 and report the expected API version.

---

## RV-002 — API Input Contract

Malformed customer identifiers shall be rejected according to the API contract.

---

## RV-003 — Upstream Data Integrity

Upstream customer data shall preserve customer identity and business meaning when transformed into the internal customer model.

---

## RV-004 — Consent Integrity

Negative marketing consent from an upstream source shall remain negative after transformation.

A release shall be blocked if consent meaning changes during mapping.

---

## RV-005 — Model Output Contract

Propensity values shall remain between 0.0 and 1.0 and shall expose the approved model version.

---

## RV-006 — Eligibility Protection

An ineligible action shall never win arbitration regardless of propensity, business value, context weight, or business lever.

---

## RV-007 — Downstream Decision Integrity

The downstream delivery record shall preserve the Next Best Action selected by the decision engine.

---

## RV-008 — Deterministic Decisioning

Repeated execution using identical inputs and the same model version shall produce consistent model and decision outputs.

---

## RV-009 — Release Smoke Suite

All release-readiness smoke tests shall pass.

Any smoke-test failure blocks the release.

---

## RV-010 — Full Regression

The complete automated regression suite shall pass before release.

---

## RV-011 — Evidence Generation

Release validation shall generate machine-readable JUnit evidence for both:

- release-readiness smoke validation
- complete regression validation

---

## RV-012 — Fail-Closed Release Gate

The release-validation runner shall return a non-zero process exit code when a mandatory validation stage fails.

A failed validation shall therefore prevent a CI/CD pipeline from treating the release as successful.