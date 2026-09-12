# NBA Decisioning Lab v1 - API Documentation

## 1. Purpose

The NBA Decisioning Lab v1 API is a local training API for a synthetic Next-Best-Action (NBA) banking decision system.

It is **not a Nordea API**, does not connect to real bank systems, and uses only synthetic customer data.

Version 1 is deliberately rule-based. It is designed to teach the separation between:

- customer data
- eligibility rules
- action scoring
- ranking
- explainability
- API delivery
- automated testing

A later version can replace or augment the rule-based scoring with machine-learning propensity models.

## 2. Technology

- **FastAPI** - defines the HTTP API and request/response models.
- **Uvicorn** - local ASGI web server that runs the FastAPI application.
- **Pydantic** - validates API data models.
- **pandas** - loads the synthetic customer dataset.
- **pytest** - automated testing.

The application object is defined in:

`src/app.py`

The API is started with:

```powershell
uvicorn src.app:app --reload
```

Meaning:

- `src.app` = load `src/app.py`
- `:app` = use the FastAPI object named `app`
- `--reload` = restart automatically when source code changes

## 3. Base URL

When run locally, the default base URL is:

`http://127.0.0.1:8000`

Interactive Swagger documentation:

`http://127.0.0.1:8000/docs`

OpenAPI schema:

`http://127.0.0.1:8000/openapi.json`

## 4. High-Level Flow

```text
Client / Browser / Postman
           |
           v
        Uvicorn
           |
           v
        FastAPI
           |
           v
 Customer Repository
           |
           v
 Decision Engine
           |
           v
Eligibility + Scoring + Ranking
           |
           v
 Next Best Action Response
```

## 5. Available Endpoints

### GET /health

Checks whether the API is running.

**Request**

```http
GET /health
```

**Example response**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

**HTTP status**

- `200 OK` - API is running.

---

### GET /nba/{customer_id}

Returns the Next Best Action for one synthetic customer.

**Path parameter**

| Name | Type | Required | Description |
|---|---|---:|---|
| `customer_id` | string | Yes | Synthetic customer ID such as `C00001` |

**Example request**

```http
GET /nba/C00001
```

**Example cURL**

```powershell
curl http://127.0.0.1:8000/nba/C00001
```

**Example PowerShell**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/nba/C00001" -Method Get
```

**Example successful response**

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
      "eligible": true,
      "reason_codes": [
        "HAS_MONTHLY_SURPLUS",
        "LOW_SAVINGS_RELATIVE_TO_INCOME"
      ]
    }
  ]
}
```

The exact result depends on the synthetic customer's data and the current decision rules.

**HTTP statuses**

- `200 OK` - customer found and decision returned.
- `404 Not Found` - customer ID does not exist.

**Example 404**

```json
{
  "detail": "Customer not found"
}
```

## 6. Candidate Actions

The v1 engine evaluates five possible actions:

| Action | Meaning |
|---|---|
| `SAVINGS_PLAN` | Recommend a savings-related action |
| `INVESTMENT_INFO` | Provide investment-related information |
| `MORTGAGE_CONSULTATION` | Suggest a mortgage discussion |
| `CREDIT_CARD_UPGRADE` | Suggest a credit-card upgrade |
| `FINANCIAL_HEALTH_CHECK` | Suggest a financial health review |

The final NBA is the highest-ranked action that remains eligible.

## 7. Response Fields

### NBAResponse

| Field | Type | Description |
|---|---|---|
| `customer_id` | string | Synthetic customer identifier |
| `next_best_action` | string | Winning action |
| `score` | number | Final score from 0.0 to 1.0 |
| `eligible` | boolean | Whether winning action is allowed |
| `reason_codes` | array[string] | Explanation for the winning decision |
| `ranked_actions` | array | All candidate actions after evaluation |

### ActionScore

Each item in `ranked_actions` contains:

| Field | Type | Description |
|---|---|---|
| `action` | string | Candidate action name |
| `score` | number | Candidate score |
| `eligible` | boolean | Whether action passed eligibility rules |
| `reason_codes` | array[string] | Reasons behind score or blocking |

## 8. Eligibility vs Scoring

This distinction is central to NBA systems.

**Scoring** asks:

> How attractive or relevant is this action for this customer?

**Eligibility** asks:

> Is the system allowed to present this action to this customer?

An action can have strong characteristics but still be blocked.

Example:

```text
Investment characteristics look strong
                |
                v
Investment consent = false
                |
                v
INVESTMENT_INFO becomes INELIGIBLE
                |
                v
Another eligible action can win
```

In v1, blocked actions receive a score of `0`.

## 9. Reason Codes

Reason codes make the decision explainable.

Examples include:

- `HAS_MONTHLY_SURPLUS`
- `LOW_SAVINGS_RELATIVE_TO_INCOME`
- `DIGITAL_ENGAGEMENT`
- `NO_MARKETING_CONSENT`
- `NO_INVESTMENT_CONSENT`
- `ALREADY_HAS_MORTGAGE`
- `HIGH_CREDIT_SCORE_BAND`
- `NEGATIVE_MONTHLY_SURPLUS`

These help testers verify **why** a decision was made rather than checking only the final action.

## 10. Main Source Files

| File | Responsibility |
|---|---|
| `src/app.py` | FastAPI endpoints |
| `src/models.py` | Pydantic request/response data models |
| `src/repository.py` | Loads and retrieves synthetic customers |
| `src/decision_engine.py` | Eligibility, scoring, ranking, final NBA |
| `src/synthetic_data.py` | Generates 20,000 synthetic customers |
| `src/demo.py` | Runs a sample decision without HTTP |
| `tests/test_api.py` | API-level tests |
| `tests/test_decision_engine.py` | Decision-engine tests |

## 11. Starting the API

From the project directory:

```text
C:\NBADecisioningLab\nba_decisioning_lab_v1
```

with the `banking` environment active:

```powershell
.\banking\Scripts\Activate.ps1
uvicorn src.app:app --reload
```

Expected terminal message:

```text
Uvicorn running on http://127.0.0.1:8000
```

Stop the server with:

`Ctrl+C`

## 12. Testing Through Swagger UI

1. Start Uvicorn.
2. Open `http://127.0.0.1:8000/docs`.
3. Expand `GET /health`.
4. Select **Try it out**.
5. Select **Execute**.
6. Confirm `200` and `{"status":"ok","version":"1.0.0"}`.
7. Expand `GET /nba/{customer_id}`.
8. Select **Try it out**.
9. Enter `C00001`.
10. Select **Execute**.
11. Inspect the winning action and full ranking.

## 13. Testing Through Postman

Create a GET request:

```text
http://127.0.0.1:8000/nba/C00001
```

No authentication, headers, or body are required in v1.

Useful tests include:

- valid customer returns `200`
- unknown customer returns `404`
- response contains `customer_id`
- response contains `next_best_action`
- winner is eligible
- ranked actions are in descending score order
- consent restrictions block relevant actions

## 14. Current Limitations

v1 is a learning system and is intentionally simple.

It currently has:

- no real bank data
- no authentication
- no authorization
- no database server
- no external banking integration
- no machine-learning model
- no model registry
- no audit database
- no production monitoring
- no Pega integration
- no GCP deployment

These are not defects in the training project; they define the scope of v1.

## 15. Planned v2 - Machine Learning

The next version can introduce the actual AI/ML layer.

Planned flow:

```text
Historical synthetic customer interactions
                 |
                 v
         Feature engineering
                 |
                 v
       Propensity ML model
                 |
                 v
P(accept action | customer, context, action)
                 |
                 v
        Eligibility rules
                 |
                 v
          NBA ranking
                 |
                 v
           API response
```

This makes the roles clear:

- **ML predicts**
- **decisioning decides**
- **QA verifies**

Possible v2 additions:

- Logistic Regression baseline
- Gradient Boosting model
- train/test split
- ROC AUC
- precision and recall
- probability calibration
- model version
- champion/challenger comparison
- regression tests between model releases

## 16. Interview-Level Explanation

A concise way to describe the project:

> I built a synthetic Next-Best-Action API using FastAPI. The system evaluates multiple candidate actions for each customer, applies eligibility constraints, scores and ranks the eligible actions, returns the winning decision with reason codes, and exposes the result through a REST endpoint. I also created automated tests for decision correctness and API behavior. The first version is rule-based so that decisioning is explicit; the next version introduces ML propensity models behind the same API.

## 17. Safety and Scope

This project is for training and portfolio use only.

Do not use it to make real financial decisions. The customer records are synthetic and the scoring rules are educational examples, not financial advice or production banking logic.
