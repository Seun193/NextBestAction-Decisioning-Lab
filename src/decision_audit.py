from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import json
import sqlite3

from .decision_audit_schema import (
    AUDIT_SCHEMA_VERSION,
)
from .models import (
    Customer,
    MembershipContext,
    NBAResponse,
)


DECISION_ENGINE_VERSION = "decision-engine-v1"
API_VERSION = "1.0.0"


@dataclass(frozen=True)
class DecisionAuditRecord:
    decision_id: str
    customer_id: str
    decision_timestamp: str

    selected_action: str
    selected_score: float
    selected_eligible: bool
    selected_reason_codes: list[str]

    ranked_actions: list[dict[str, Any]]

    customer_snapshot: dict[str, Any]
    membership_snapshot: dict[str, Any] | None
    membership_used: bool

    decision_engine_version: str
    model_version: str | None
    api_version: str
    audit_schema_version: str


def _model_to_dict(
    model: Any,
) -> dict[str, Any]:
    """
    Convert a Pydantic model into a plain dictionary.

    Supports both modern model_dump() and the older dict()
    interface so the audit layer is not unnecessarily coupled
    to one Pydantic generation.
    """

    if hasattr(
        model,
        "model_dump",
    ):
        return model.model_dump(
            mode="json"
        )

    return model.dict()


def _serialize_json(
    value: Any,
) -> str:
    """
    Produce deterministic JSON for persisted audit evidence.
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )


def _utc_timestamp() -> str:
    """
    Return an ISO-8601 UTC decision timestamp.
    """

    return (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="milliseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def _new_decision_id() -> str:
    """
    Generate a globally unique synthetic decision identifier.
    """

    return (
        "DEC-"
        + uuid4().hex.upper()
    )


def _validate_decision_consistency(
    customer: Customer,
    decision: NBAResponse,
) -> None:
    """
    Protect the audit store from internally contradictory
    decision objects.

    The audit layer records decision output. It must not
    reinterpret or repair it.
    """

    if (
        decision.customer_id
        != customer.customer_id
    ):
        raise ValueError(
            "Decision customer_id does not "
            "match Customer snapshot"
        )

    if not decision.ranked_actions:
        raise ValueError(
            "Decision ranked_actions "
            "must not be empty"
        )

    winner = (
        decision.ranked_actions[0]
    )

    if (
        winner.action
        != decision.next_best_action
    ):
        raise ValueError(
            "Selected action does not match "
            "the first ranked action"
        )

    if (
        winner.score
        != decision.score
    ):
        raise ValueError(
            "Selected score does not match "
            "the first ranked action"
        )

    if (
        winner.eligible
        != decision.eligible
    ):
        raise ValueError(
            "Selected eligibility does not match "
            "the first ranked action"
        )

    if (
        winner.reason_codes
        != decision.reason_codes
    ):
        raise ValueError(
            "Selected reason codes do not match "
            "the first ranked action"
        )


def persist_decision_audit(
    connection: sqlite3.Connection,
    customer: Customer,
    membership: MembershipContext | None,
    decision: NBAResponse,
    *,
    decision_id: str | None = None,
    decision_timestamp: str | None = None,
    decision_engine_version: str = DECISION_ENGINE_VERSION,
    model_version: str | None = None,
    api_version: str = API_VERSION,
) -> str:
    """
    Persist one immutable decision audit record.

    The caller supplies an already-computed decision.
    This function does not calculate eligibility, scoring,
    membership adjustments, or ranking.

    Returns the persisted decision_id.
    """

    _validate_decision_consistency(
        customer,
        decision,
    )

    final_decision_id = (
        decision_id
        or _new_decision_id()
    )

    final_timestamp = (
        decision_timestamp
        or _utc_timestamp()
    )

    customer_snapshot = (
        _model_to_dict(
            customer
        )
    )

    membership_snapshot = (
        _model_to_dict(
            membership
        )
        if membership is not None
        else None
    )

    ranked_actions = [
        _model_to_dict(
            action
        )
        for action
        in decision.ranked_actions
    ]

    selected_reason_codes_json = (
        _serialize_json(
            list(
                decision.reason_codes
            )
        )
    )

    ranked_actions_json = (
        _serialize_json(
            ranked_actions
        )
    )

    customer_snapshot_json = (
        _serialize_json(
            customer_snapshot
        )
    )

    membership_snapshot_json = (
        _serialize_json(
            membership_snapshot
        )
        if membership_snapshot
        is not None
        else None
    )

    sql = """
        INSERT INTO decision_audits (
            decision_id,
            customer_id,
            decision_timestamp,
            selected_action,
            selected_score,
            selected_eligible,
            selected_reason_codes_json,
            ranked_actions_json,
            customer_snapshot_json,
            membership_snapshot_json,
            membership_used,
            decision_engine_version,
            model_version,
            api_version,
            audit_schema_version
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?
        )
    """

    values = (
        final_decision_id,
        customer.customer_id,
        final_timestamp,
        decision.next_best_action,
        decision.score,
        int(
            decision.eligible
        ),
        selected_reason_codes_json,
        ranked_actions_json,
        customer_snapshot_json,
        membership_snapshot_json,
        int(
            membership is not None
        ),
        decision_engine_version,
        model_version,
        api_version,
        AUDIT_SCHEMA_VERSION,
    )

    with connection:
        connection.execute(
            sql,
            values,
        )

    return final_decision_id


def get_decision_audit(
    connection: sqlite3.Connection,
    decision_id: str,
) -> DecisionAuditRecord | None:
    """
    Retrieve one persisted audit record by decision_id.
    """

    row = connection.execute(
        """
        SELECT
            decision_id,
            customer_id,
            decision_timestamp,
            selected_action,
            selected_score,
            selected_eligible,
            selected_reason_codes_json,
            ranked_actions_json,
            customer_snapshot_json,
            membership_snapshot_json,
            membership_used,
            decision_engine_version,
            model_version,
            api_version,
            audit_schema_version
        FROM decision_audits
        WHERE decision_id = ?
        """,
        (
            decision_id,
        ),
    ).fetchone()

    if row is None:
        return None

    return DecisionAuditRecord(
        decision_id=row[0],
        customer_id=row[1],
        decision_timestamp=row[2],
        selected_action=row[3],
        selected_score=row[4],
        selected_eligible=bool(
            row[5]
        ),
        selected_reason_codes=json.loads(
            row[6]
        ),
        ranked_actions=json.loads(
            row[7]
        ),
        customer_snapshot=json.loads(
            row[8]
        ),
        membership_snapshot=(
            json.loads(
                row[9]
            )
            if row[9] is not None
            else None
        ),
        membership_used=bool(
            row[10]
        ),
        decision_engine_version=row[11],
        model_version=row[12],
        api_version=row[13],
        audit_schema_version=row[14],
    )