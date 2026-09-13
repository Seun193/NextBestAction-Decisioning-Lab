# NBA API Contract Rules v1

## Purpose

This document defines the externally observable HTTP contract for the NBA Decisioning Lab API.

The contract covers successful responses, malformed requests, missing resources, unsupported operations, response structure, and safe error behaviour.

---

## API-001 — Health Endpoint

`GET /health` shall:

- return HTTP `200`
- return JSON
- contain `status`
- contain `version`
- return `status = "ok"`

---

## API-002 — Existing Customer

`GET /nba/{customer_id}` with a correctly formatted and existing customer ID shall:

- return HTTP `200`
- return JSON
- return the requested `customer_id`
- return a Next Best Action response conforming to the published response structure

---

## API-003 — Unknown Customer

A correctly formatted customer ID that does not exist shall:

- return HTTP `404`
- return a controlled JSON error response
- return `detail = "Customer not found"`

Example:

`C99999`

---

## API-004 — Malformed Customer ID

A customer ID that does not match the required format shall be rejected before customer lookup.

Required format:

`C` followed by exactly five digits.

Valid example:

`C00001`

Invalid examples:

- `DOES_NOT_EXIST`
- `C1234`
- `C123456`
- `X00001`
- `C12A45`

Malformed customer IDs shall return HTTP `422`.

---

## API-005 — Unsupported HTTP Method

An unsupported HTTP method on an existing NBA route shall return HTTP `405 Method Not Allowed`.

---

## API-006 — Unknown Endpoint

A request to an undefined API route shall return HTTP `404`.

---

## API-007 — Score Range

The winning NBA score and every ranked action score shall be within:

`0.0 <= score <= 1.0`

---

## API-008 — Ranked Action Contract

Every item in `ranked_actions` shall contain:

- `action`
- `score`
- `eligible`
- `reason_codes`

Field types shall conform to the published API model.

---

## API-009 — JSON Content Type

Successful NBA responses and controlled API error responses shall use a JSON content type.

---

## API-010 — Safe Error Responses

Controlled error responses shall not expose internal implementation details such as:

- filesystem paths
- Python tracebacks
- SQLite implementation details
- repository source-file names
- decision-engine source-file names