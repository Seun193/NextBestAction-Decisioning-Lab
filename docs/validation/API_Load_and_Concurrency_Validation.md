
Now put this in `API_Load_and_Concurrency_Validation.md`:

````markdown
# API Load and Concurrency Validation

## Objective

Evaluate the Next Best Action API under increasing concurrent traffic while validating both response correctness and performance behaviour.

The validation used Locust 2.46.5 with Python 3.13.1 against the local FastAPI application.

## Load Model

Simulated users:

- select a random contract-valid customer from `C00001` to `C20000`
- call `GET /nba/{customer_id}`
- validate critical response-contract fields
- wait approximately one second
- repeat

Dynamic requests are reported as:

`/nba/[customer_id]`

This keeps performance statistics aggregated across customer IDs.

## Performance Criteria

### Normal Load

For up to 50 concurrent users:

- failure rate: `0%`
- p95: `< 500 ms`
- p99: `< 1000 ms`

### Surge Load

For higher concurrency:

- failure rate: `0%`
- p95: `< 1000 ms`
- p99: `< 2000 ms`
- service remains responsive after testing

## Single-Worker NBA Results

| Users | Requests | Failures | RPS | Avg | p50 | p95 | p99 | Result |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 29 | 0 | 1.02 | 9 ms | 9 ms | 17 ms | 28 ms | PASS |
| 10 | 567 | 0 | 9.63 | 11 ms | 10 ms | 25 ms | 54 ms | PASS |
| 25 | 1,409 | 0 | 23.83 | 13 ms | 10 ms | 32 ms | 75 ms | PASS |
| 50 | 2,835 | 0 | 47.97 | 8 ms | 8 ms | 18 ms | 32 ms | PASS |
| 100 | 4,887 | 0 | 82.72 | 146 ms | 56 ms | 540 ms | 690 ms | PASS |
| 150 | 5,868 | 0 | 97.57 | 408 ms | 390 ms | 920 ms | 1,100 ms | PASS |
| 175 repeat | 6,038 | 0 | 98.23 | 605 ms | 370 ms | 2,200 ms | 3,600 ms | FAIL |
| 200 | 5,266 | 0 | 86.96 | 1,070 ms | 870 ms | 2,500 ms | 7,500 ms | FAIL |

## Single-Worker Saturation Finding

The application remained functionally correct at high concurrency, but latency increased sharply between 150 and 175 concurrent users.

At 175 users:

```text
p95 = 2200 ms
p99 = 3600 ms