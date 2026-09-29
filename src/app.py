from fastapi import FastAPI, HTTPException, Path

from .membership_decisioning import decide_with_membership
from .repository import (
    get_customer,
    get_membership_context,
)
from .models import NBAResponse


app = FastAPI(
    title="NBA Decisioning Lab",
    version="1.0.0",
    description="Synthetic Next-Best-Action decisioning demonstration API",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
    }


@app.get(
    "/nba/{customer_id}",
    response_model=NBAResponse,
)
def get_nba(
    customer_id: str = Path(
        ...,
        pattern=r"^C\d{5}$",
        description="Synthetic customer ID in the format C#####",
    ),
):
    customer = get_customer(
        customer_id
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    membership = get_membership_context(
        customer_id
    )

    return decide_with_membership(
        customer,
        membership,
    )