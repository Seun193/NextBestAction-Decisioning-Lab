# API Contract and Negative Testing

## Objective

Validate the externally observable behaviour of the NBA Decisioning Lab API, with particular emphasis on invalid input, missing resources, unsupported operations, response structure, and safe error handling.

---

## Baseline

Before API contract hardening, the project test suite contained:

- 38 passing tests
- 1 known Starlette/AnyIO deprecation warning

The existing API accepted any string as the `{customer_id}` path parameter and passed that value directly to the repository layer.

For example:

```text
GET /nba/DOES_NOT_EXIST
---

## Contract Hardening Implementation

The API was updated to validate the `{customer_id}` path parameter before repository lookup.

The accepted identifier format is:

```text
^C\d{5}$