# NBA Decisioning Lab v1 - API Documentation

## 1. Purpose

The NBA Decisioning Lab v1 API is a local demonstration API for a synthetic Next-Best-Action (NBA) banking decision system.

It is **not a Nordea API**, does not connect to real bank systems, and uses only synthetic customer data.

Version 1 is deliberately rule-based. It demonstrates the separation between:

- customer data
- eligibility rules
- action scoring
- ranking
- explainability
- API delivery
- automated testing

A later version can replace or augment the rule-based scoring with machine-learning propensity models.

---

## 2. Technology

- **FastAPI** - defines the HTTP API and request/response models.
- **Uvicorn** - local ASGI web server that runs the FastAPI application.
- **Pydantic** - validates API data models.
- **SQLite** - stores the synthetic customer dataset used by the decisioning API.
- **Python sqlite3** - provides parameterized database access.
- **pytest** - automated testing.

The application object is defined in:

`src/app.py`

The API is started with:

```powershell
uvicorn src.app:app --reload