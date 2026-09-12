# NBA Decisioning Lab v1

A synthetic Next-Best-Action (NBA) training project for learning how enterprise decisioning systems combine:

- customer data
- eligibility rules
- action scoring
- explainability
- REST APIs
- automated testing

This version is intentionally **rule-based**. Version 2 will introduce machine learning propensity models so that the difference between "AI" and "decisioning" stays clear.

## Architecture

Synthetic customer data
        |
        v
Eligibility checks
        |
        v
Rule-based action scoring
        |
        v
Rank candidate actions
        |
        v
Next Best Action
        |
        v
FastAPI endpoint
        |
        v
Automated tests

## Candidate actions

1. SAVINGS_PLAN
2. INVESTMENT_INFO
3. MORTGAGE_CONSULTATION
4. CREDIT_CARD_UPGRADE
5. FINANCIAL_HEALTH_CHECK

## Quick start

### 1. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Generate synthetic data

```powershell
python -m src.synthetic_data
```

This creates:

```text
data/customers.csv
```

with 20,000 completely synthetic customers.

### 4. Run a local decision

```powershell
python -m src.demo
```

### 5. Start the API

```powershell
uvicorn src.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

### 6. Run tests

```powershell
pytest -q
```

## Example API response

```json
{
  "customer_id": "C00001",
  "next_best_action": "SAVINGS_PLAN",
  "score": 0.74,
  "eligible": true,
  "reason_codes": [
    "HAS_MONTHLY_SURPLUS",
    "LOW_SAVINGS_RELATIVE_TO_INCOME",
    "DIGITAL_ENGAGEMENT"
  ],
  "ranked_actions": [
    {
      "action": "SAVINGS_PLAN",
      "score": 0.74,
      "eligible": true
    }
  ]
}
```

## Learning objectives

After v1 you should be able to explain:

- what an NBA decision engine is
- the difference between eligibility and ranking
- why the highest raw score may not be allowed
- how decision outcomes can be tested
- how reason codes improve explainability
- how APIs expose decisions to downstream channels

## Next phase

v2 will add:

- synthetic historical offer/response data
- scikit-learn propensity models
- train/test split
- ROC AUC / precision / recall
- probability calibration
- model versioning
- model-vs-rule testing
