\# SQLite Data Layer Validation



\## Objective



Migrate the NBA Decisioning Lab customer data source from CSV-based lookup to SQLite while preserving existing NBA behavior.



The goal was to simulate a realistic enterprise change where the storage layer changes but the decisioning logic must remain stable.



\---



\## Starting Point



The NBA Decisioning Lab already had:



\- 20,000 synthetic customers

\- Rule-based NBA engine

\- FastAPI application

\- Eligibility rules

\- Scoring and ranking

\- Reason codes

\- Existing pytest coverage

\- `/health` endpoint

\- `/nba/{customer\_id}` endpoint



Originally, customer data was loaded directly from:



```text

data/customers.csv

