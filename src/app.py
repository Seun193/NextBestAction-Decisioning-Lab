from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Response,
)

from .decision_audit import (
    persist_decision_audit,
)
from .decision_audit_schema import (
    create_decision_audit_schema,
    validate_customer_table,
    verify_decision_audit_schema,
)
from .membership_decisioning import (
    decide_with_membership,
)
from .models import (
    Customer,
    MembershipContext,
    NBAResponse,
)
from .repository import (
    get_connection,
    get_customer,
    get_membership_context,
)


APP_VERSION = "1.0.0"


app = FastAPI(
    title="NBA Decisioning Lab",
    version=APP_VERSION,
    description=(
        "Synthetic Next-Best-Action "
        "decisioning demonstration API"
    ),
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
    }


def persist_api_decision(
    customer: Customer,
    membership: MembershipContext | None,
    decision: NBAResponse,
) -> str:
    """
    Persist one successfully calculated API decision.

    The audit schema is created safely when required.
    Audit persistence is deliberately separate from
    decision calculation so it cannot alter eligibility,
    scoring, membership relevance, or ranking.
    """

    connection = get_connection()

    try:
        validate_customer_table(
            connection
        )

        create_decision_audit_schema(
            connection
        )

        verify_decision_audit_schema(
            connection
        )

        return persist_decision_audit(
            connection,
            customer,
            membership,
            decision,
            api_version=APP_VERSION,
        )

    finally:
        connection.close()


@app.get(
    "/nba/{customer_id}",
    response_model=NBAResponse,
)
def get_nba(
    response: Response,
    customer_id: str = Path(
        ...,
        pattern=r"^C\d{5}$",
        description=(
            "Synthetic customer ID "
            "in the format C#####"
        ),
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

    decision = decide_with_membership(
        customer,
        membership,
    )

    try:
        decision_id = persist_api_decision(
            customer,
            membership,
            decision,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Decision audit "
                "persistence failed"
            ),
        ) from exc

    response.headers[
        "X-Decision-ID"
    ] = decision_id

    return decision