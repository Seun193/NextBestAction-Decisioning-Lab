# Batch Reconciliation Validation

## Objective

Validate NBA integration consistency across the full synthetic customer population by comparing SQLite-driven expected decisions with responses returned by the live NBA API.

This validation extends the detailed single-customer reconciliation utility to population-scale testing.

---

## Validation Scope

For every selected customer, the reconciler compares:

- HTTP status
- customer ID
- next best action
- score
- eligibility
- reason codes
- ranked actions

A customer passes only when every required comparison matches.

This is an integration-consistency test.

Independent business-rule correctness remains covered separately by the business-rule validation suite.

---

## Batch Reconciliation Design

The validation flow is:

```text
SQLite customer
      |
      v
Current decision engine
      |
      v
Expected NBA response
      |
      +-------------------+
                          |
                          v
                    Live HTTP API
                          |
                          v
                    Actual response
                          |
                          v
                Field-by-field comparison
                          |
                          v
                     PASS / FAIL
```

The batch reconciler also reports:

- total customers checked
- total customers passed
- total customers failed
- reconciliation match rate
- elapsed time
- sequential processing throughput

For failed customers, the reconciler can record:

- customer ID
- failing field
- expected value
- actual value

---

## Progressive Validation

The reconciler was exercised progressively before running the complete customer population.

### 10 Customers

```text
Customers checked : 10
Passed            : 10
Failed            : 0
Match rate        : 100.0000%
Elapsed time      : 0.13 seconds
Throughput        : 74.23 customers/second
OVERALL: PASS
```

### 100 Customers

```text
Customers checked : 100
Passed            : 100
Failed            : 0
Match rate        : 100.0000%
Elapsed time      : 0.45 seconds
Throughput        : 222.83 customers/second
OVERALL: PASS
```

### 1,000 Customers

```text
Customers checked : 1,000
Passed            : 1,000
Failed            : 0
Match rate        : 100.0000%
Elapsed time      : 4.21 seconds
Throughput        : 237.61 customers/second
OVERALL: PASS
```

---

## Full-Population Reconciliation

The complete 20,000-customer synthetic dataset was reconciled through the live NBA API.

Command:

```powershell
python -m src.batch_reconcile_db_api `
    --report .\reports\batch_reconciliation_20000.csv
```

Result:

```text
Customers checked : 20,000
Passed            : 20,000
Failed            : 0
Match rate        : 100.0000%
Elapsed time      : 153.00 seconds
Throughput        : 130.72 customers/second
OVERALL: PASS
```

The full-population validation produced no reconciliation mismatches.

All 20,000 SQLite customer records produced NBA results that matched the responses returned through the live HTTP API.

---

## Reconciliation Test Coverage

Dedicated automated tests were added for the batch-reconciliation comparison logic.

The tests verify that the reconciler:

- accepts a completely matching response
- detects an incorrect next best action
- detects an incorrect score
- detects an incorrect HTTP status

Test result:

```text
4 passed
```

The complete project regression suite then reported:

```text
56 passed
1 known dependency warning
```

The remaining warning originates from the Starlette test client and the deprecated `anyio.abc.BlockingPortal` alias.

It does not represent a failure in the NBA application logic.

---

## Generated Reconciliation Reports

The batch reconciler can create machine-readable CSV evidence.

Examples generated during validation include:

```text
reports/batch_reconciliation_100.csv
reports/batch_reconciliation_1000.csv
reports/batch_reconciliation_20000.csv
```

These generated reports are local test artifacts and are excluded from Git version control.

The source code and validation methodology are committed, while large generated evidence files remain reproducible locally.

---

## Performance Observation

Sequential reconciliation throughput changed as the batch size increased:

| Customers | Elapsed Time | Throughput |
|---:|---:|---:|
| 10 | 0.13 s | 74.23 customers/sec |
| 100 | 0.45 s | 222.83 customers/sec |
| 1,000 | 4.21 s | 237.61 customers/sec |
| 20,000 | 153.00 s | 130.72 customers/sec |

The 20,000-customer run remained functionally correct but showed lower sustained sequential throughput than the shorter runs.

This is recorded as a performance observation rather than a defect.

The reconciler sends requests sequentially, one customer at a time. Therefore these throughput figures are not measurements of concurrent API capacity.

---

## Functional Validation vs Load Testing

Batch reconciliation and load testing answer different questions.

```text
Batch reconciliation
        |
        v
Does every customer's expected NBA
match the API result?
```

```text
Load testing
        |
        v
How does the API behave when many
requests arrive at the same time?
```

The current reconciliation confirms functional consistency across a large population.

Dedicated load testing will later measure:

- requests per second
- concurrent users
- p50 latency
- p95 latency
- p99 latency
- HTTP error rate
- CPU usage
- memory usage
- database response time
- system recovery after traffic spikes

---

## Promotion Traffic Scenario

A future operational scenario will simulate a promotion or banking campaign that suddenly increases customer activity.

For example:

```text
Normal customer traffic
        |
        v
New savings or product campaign
        |
        v
Sharp increase in customer engagement
        |
        v
5x - 10x API request volume
        |
        v
Measure latency, throughput,
errors and system recovery
```

This scenario will test whether the NBA service remains reliable when business activity causes a sudden traffic surge.

---

## Scalability Direction

The current 20,000-customer dataset is appropriate for functional and integration validation.

Future synthetic datasets can extend the population toward:

```text
20,000
   |
   v
100,000
   |
   v
1,000,000 customers
```

Larger datasets will support investigation of:

- database-volume behaviour
- SQLite indexing performance
- query performance
- bulk data-quality validation
- large reconciliation workloads
- memory usage
- data ingestion performance
- API load testing
- promotion-driven traffic spikes
- stress testing
- recovery testing

A larger customer population and higher concurrent request traffic will be tested separately because data volume and API traffic represent different performance dimensions.

---

## Validation Result

Full-population batch reconciliation completed successfully.

- 20,000 customers checked
- 20,000 customers passed
- 0 customers failed
- 100.0000% reconciliation match rate
- 153.00-second full-population run
- 130.72 customers/second sustained sequential reconciliation throughput
- 4 dedicated batch-reconciliation tests passed
- 56-test complete regression suite remains green

The current NBA implementation is internally consistent across the complete synthetic customer population tested.

The observed reduction in sustained throughput at the 20,000-customer scale has been retained as a performance observation for future scalability and load-testing work.