# NBA Batch Reconciliation Rules v1

## Purpose

Define the validation requirements for population-scale reconciliation between SQLite customer data, expected NBA decisions, and the externally exposed NBA API.

The batch reconciler complements the detailed single-customer reconciliation utility.

---

## REC-001 — Customer Population

The reconciler shall be able to process multiple customer records from the SQLite customer database.

It shall support:

- limited validation runs for development
- full-population validation runs

---

## REC-002 — Expected Decision

For each customer, the reconciler shall derive the expected NBA response from the database customer record using the current decision engine.

This validates integration consistency.

Independent business-rule correctness remains covered by the business-rule validation suite.

---

## REC-003 — API Comparison

For every processed customer, the following shall be compared:

- HTTP status
- customer ID
- next best action
- score
- eligibility
- reason codes
- ranked actions

---

## REC-004 — Match Classification

Each processed customer shall receive one overall result:

- PASS
- FAIL

A customer passes only when all required reconciliation fields match.

---

## REC-005 — Failure Evidence

For failed customers, the reconciler shall record:

- customer ID
- failing field
- expected value
- actual value

---

## REC-006 — Aggregate Summary

The reconciler shall report:

- customers checked
- customers passed
- customers failed
- match rate
- elapsed time
- customers processed per second

---

## REC-007 — Machine-Readable Report

The reconciler shall optionally write reconciliation results to a CSV report for further analysis.

---

## REC-008 — API Availability

If the API cannot be reached, the reconciler shall terminate with a clear error instead of silently recording customer mismatches.

---

## REC-009 — Exit Status

The command shall exit:

- `0` when every processed customer passes
- non-zero when one or more customers fail

This allows future use in CI/CD pipelines.

---

## REC-010 — Scalability

The reconciliation design shall support future expansion from the current 20,000-customer dataset to substantially larger synthetic populations without changing the validation contract.