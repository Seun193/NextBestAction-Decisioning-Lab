# Next Best Action Decisioning — Architecture

```mermaid
flowchart LR
    A[Synthetic Customer Data] --> B[SQLite]
    B --> C[Repository Layer]
    C --> D[Eligibility Rules]
    D --> E[Action Scoring]
    E --> F[Ranking & Arbitration]
    F --> G[Next Best Action]
    G --> H[FastAPI]

    B --> I[QA Reconciliation]
    H --> I
    I --> J[Regression Validation]
```

## Validation focus

The system is evaluated across three concerns:

**Data integrity**  
Is the correct customer record being consumed?

**Decision integrity**  
Are eligibility, score, ranking and reason codes consistent with the input?

**Regression safety**  
Can infrastructure or data-layer changes occur without altering established decision behaviour?
