# NBA Scale and Volume Validation Rules v1

## Purpose

Define the validation expectations for large synthetic customer populations in the Next Best Action Decisioning Lab.

The objective is to verify that the customer-data generation and SQLite ingestion pipeline can process substantially larger datasets without row loss, corruption, or regression of the existing application.

## Scope

Volume-validation sizes:

- 20,000 customers — development baseline
- 100,000 customers — intermediate scale
- 1,000,000 customers — large-volume scale

This validation focuses on data generation, SQLite ingestion, row-count integrity, and processing performance.

Concurrent API traffic is tested separately as load testing.

## SV-001 — Configurable Customer Population

The synthetic-data generator shall support a configurable number of customers.

The existing default shall remain 20,000 customers.

## SV-002 — Deterministic Data Generation

Synthetic generation shall continue to support a fixed random seed so that datasets are reproducible.

## SV-003 — Large Dataset Isolation

Large generated CSV and SQLite files shall remain outside Git version control.

Generated scale artifacts shall be stored under:

`data/scale/`

## SV-004 — Batched SQLite Loading

The SQLite loader shall process large CSV files in bounded batches rather than loading the complete dataset into memory before insertion.

The default batch size shall be configurable.

## SV-005 — Source-to-Database Row Integrity

For every volume-validation run:

`source row count = inserted row count = SQLite row count`

Any mismatch shall fail validation.

## SV-006 — Existing Workflow Compatibility

Running the generator without scale parameters shall preserve the existing 20,000-customer development workflow.

## SV-007 — Regression Protection

After scale-related implementation changes, the complete automated regression suite shall remain passing.

## SV-008 — Performance Evidence

The volume loader shall report:

- CSV inspection time
- SQLite load time
- total elapsed time
- SQLite load throughput in rows per second

## SV-009 — API Contract Separation

Customer identifiers beyond the current API contract `C#####` may be used for data-layer volume testing.

They shall not be interpreted as valid API customer identifiers.

Volume testing and concurrent API load testing are separate validation activities.

## Pass Criteria

A volume-validation run passes when:

- the requested dataset is generated successfully
- the SQLite loader completes successfully
- source, inserted, and database row counts match
- no existing automated regression tests fail
- generated large-scale artifacts remain outside Git