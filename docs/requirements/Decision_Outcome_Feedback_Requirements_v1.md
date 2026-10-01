# Decision Outcome and Feedback Requirements v1

## Purpose

This specification defines requirements for capturing, persisting, validating, reconciling, and analysing customer outcomes associated with Next Best Action decisions in the synthetic banking Decisioning Lab.

The capability must make it possible to determine:

- which audited decision an outcome belongs to
- which customer received the original decision
- which selected action the outcome relates to
- what customer interaction or outcome occurred
- when the event occurred
- when the event was received by the system
- whether duplicate delivery occurred
- whether the event reconciles to the immutable decision audit
- whether conversion value was recorded correctly
- how decision outcomes perform across actions and customer contexts

All data in this project is synthetic.

---

## Scope

The Decision Outcome and Feedback capability will add:

- persistent decision-outcome events
- event identifiers
- decision-to-outcome traceability
- customer and selected-action reconciliation
- controlled outcome-event types
- event-time and ingestion-time tracking
- idempotent event ingestion
- outcome API validation
- transactional persistence
- outcome data-quality validation
- decision-performance analytics
- membership-aware outcome segmentation
- release-gate coverage

The initial version is an outcome-measurement and attribution layer.

Outcome data must not alter the historical decision audit and must not yet influence future decision scores, eligibility, ranking, or propensity-model behaviour.

---

## Supported Outcome Event Types

The initial controlled event types are:

```text
VIEWED
CLICKED
ACCEPTED
DISMISSED
CONVERTED