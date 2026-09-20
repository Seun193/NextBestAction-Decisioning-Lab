# NBA API Load Validation Rules v1

## Purpose

Define the concurrency, latency, reliability, and recovery expectations for the Next Best Action Decisioning API.

The objective is to verify that the API remains functionally correct and responsive as concurrent traffic increases, and to identify saturation behaviour under controlled load.

## Scope

Primary endpoint:

`GET /nba/{customer_id}`

Control endpoint:

`GET /health`

Load testing is performed with Locust using contract-valid synthetic customer identifiers from:

`C00001` to `C20000`

Large-volume data tests using 100,000 and 1,000,000 records are covered separately by scale and volume validation.

## AL-001 — Functional Integrity Under Load

Every successful NBA request shall continue to satisfy the response contract.

The load test shall validate:

- HTTP status `200`
- requested `customer_id` is preserved
- `next_best_action` is present
- `eligible` is boolean
- `reason_codes` is a list
- `ranked_actions` is a non-empty list

A response that violates these checks shall be recorded as a Locust failure.

## AL-002 — Request Aggregation

Dynamic customer URLs shall be aggregated in Locust under:

`/nba/[customer_id]`

This prevents individual customer IDs from fragmenting performance statistics.

## AL-003 — Normal Load Criteria

For normal-load scenarios up to 50 concurrent users:

- functional/request failure rate shall be `0%`
- p95 response time shall be below `500 ms`
- p99 response time shall be below `1000 ms`

## AL-004 — Surge Load Criteria

For surge scenarios above 50 concurrent users:

- functional/request failure rate shall be `0%`
- p95 response time shall be below `1000 ms`
- p99 response time shall be below `2000 ms`
- the service shall remain responsive after the test

## AL-005 — Throughput

Requests per second shall be measured and reported.

RPS is an observational metric rather than a fixed pass/fail threshold because results depend on local hardware, server configuration, operating-system scheduling, and test topology.

## AL-006 — Recovery

After high-concurrency testing, the `/health` endpoint shall remain responsive and return:

```json
{
  "status": "ok",
  "version": "1.0.0"
}