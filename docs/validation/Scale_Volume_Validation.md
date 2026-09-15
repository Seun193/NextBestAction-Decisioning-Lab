# Scale and Volume Validation

## Objective

Validate that the synthetic customer-data pipeline can scale from the normal 20,000-customer development baseline to 100,000 and 1,000,000 customer records while preserving row integrity and the existing application regression baseline.

## Implementation

The synthetic-data generator was extended to support configurable customer counts and output paths.

Example:

```powershell
python -m src.synthetic_data `
    --customers 100000 `
    --output data\scale\customers_100k.csv