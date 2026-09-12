from fastapi import FastAPI, HTTPException

from .decision_engine import decide
from .repository import get_customer
from .models import NBAResponse


app = FastAPI(
    title="NBA Decisioning Lab",
    version="1.0.0",
    description="Synthetic Next-Best-Action decisioning training API",
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/nba/{customer_id}", response_model=NBAResponse)
def get_nba(customer_id: str):
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return decide(customer)
