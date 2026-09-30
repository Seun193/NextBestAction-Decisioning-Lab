from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import json
import sqlite3


REQUIRED_RANKED_ACTION_FIELDS = {
    "action",
    "score",
    "eligible",
    "reason_codes",
}


@dataclass(frozen=True)
class AuditQualityIssue:
    decision_id: str | None
    code: str
    detail: str


def count_decision_audits(
    connection: sqlite3.Connection,
) -> int:
    """
    Return the number of persisted decision audit records.
    """

    return connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_audits
        """
    ).fetchone()[0]


def _add_issue(
    issues: list[AuditQualityIssue],
    decision_id: str | None,
    code: str,
    detail: str,
) -> None:
    issues.append(
        AuditQualityIssue(
            decision_id=decision_id,
            code=code,
            detail=detail,
        )
    )


def _decode_json_field(
    *,
    value: str | None,
    field_name: str,
    expected_type: type,
    decision_id: str | None,
    issues: list[AuditQualityIssue],
) -> Any | None:
    if value is None:
        _add_issue(
            issues,
            decision_id,
            "INVALID_SERIALIZED_FIELD",
            f"{field_name} is NULL",
        )
        return None

    try:
        decoded = json.loads(
            value
        )
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        _add_issue(
            issues,
            decision_id,
            "INVALID_SERIALIZED_FIELD",
            f"{field_name} contains invalid JSON",
        )
        return None

    if not isinstance(
        decoded,
        expected_type,
    ):
        _add_issue(
            issues,
            decision_id,
            "INVALID_SERIALIZED_FIELD",
            (
                f"{field_name} has invalid "
                "serialized structure"
            ),
        )
        return None

    return decoded


def validate_decision_audit_quality(
    connection: sqlite3.Connection,
) -> list[AuditQualityIssue]:
    """
    Validate persisted decision-audit integrity.

    This function does not recalculate decisions.
    It validates the evidence already stored in SQLite.
    """

    issues: list[
        AuditQualityIssue
    ] = []

    duplicate_rows = connection.execute(
        """
        SELECT
            decision_id,
            COUNT(*)
        FROM decision_audits
        WHERE decision_id IS NOT NULL
          AND TRIM(decision_id) <> ''
        GROUP BY decision_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    for (
        decision_id,
        duplicate_count,
    ) in duplicate_rows:
        _add_issue(
            issues,
            decision_id,
            "DUPLICATE_DECISION_ID",
            (
                "decision_id occurs "
                f"{duplicate_count} times"
            ),
        )

    rows = connection.execute(
        """
        SELECT
            rowid,
            decision_id,
            customer_id,
            selected_action,
            selected_score,
            selected_eligible,
            selected_reason_codes_json,
            ranked_actions_json,
            customer_snapshot_json,
            membership_snapshot_json,
            membership_used
        FROM decision_audits
        """
    ).fetchall()

    for row in rows:
        (
            rowid,
            decision_id,
            customer_id,
            selected_action,
            selected_score,
            selected_eligible,
            selected_reason_codes_json,
            ranked_actions_json,
            customer_snapshot_json,
            membership_snapshot_json,
            membership_used,
        ) = row

        issue_identifier = (
            decision_id
            if (
                decision_id is not None
                and str(
                    decision_id
                ).strip()
            )
            else f"ROWID:{rowid}"
        )

        if (
            decision_id is None
            or not str(
                decision_id
            ).strip()
        ):
            _add_issue(
                issues,
                issue_identifier,
                "MISSING_DECISION_ID",
                "decision_id is missing",
            )

        if (
            customer_id is None
            or not str(
                customer_id
            ).strip()
        ):
            _add_issue(
                issues,
                issue_identifier,
                "MISSING_CUSTOMER_ID",
                "customer_id is missing",
            )

        if (
            selected_action is None
            or not str(
                selected_action
            ).strip()
        ):
            _add_issue(
                issues,
                issue_identifier,
                "MISSING_SELECTED_ACTION",
                "selected_action is missing",
            )

        selected_reason_codes = (
            _decode_json_field(
                value=(
                    selected_reason_codes_json
                ),
                field_name=(
                    "selected_reason_codes_json"
                ),
                expected_type=list,
                decision_id=(
                    issue_identifier
                ),
                issues=issues,
            )
        )

        ranked_actions = (
            _decode_json_field(
                value=ranked_actions_json,
                field_name=(
                    "ranked_actions_json"
                ),
                expected_type=list,
                decision_id=(
                    issue_identifier
                ),
                issues=issues,
            )
        )

        customer_snapshot = (
            _decode_json_field(
                value=customer_snapshot_json,
                field_name=(
                    "customer_snapshot_json"
                ),
                expected_type=dict,
                decision_id=(
                    issue_identifier
                ),
                issues=issues,
            )
        )

        membership_snapshot = None

        if (
            membership_snapshot_json
            is not None
        ):
            membership_snapshot = (
                _decode_json_field(
                    value=(
                        membership_snapshot_json
                    ),
                    field_name=(
                        "membership_snapshot_json"
                    ),
                    expected_type=dict,
                    decision_id=(
                        issue_identifier
                    ),
                    issues=issues,
                )
            )

        if (
            membership_used == 1
            and membership_snapshot_json
            is None
        ):
            _add_issue(
                issues,
                issue_identifier,
                "MISSING_MEMBERSHIP_SNAPSHOT",
                (
                    "membership_used is true "
                    "but no snapshot exists"
                ),
            )

        if (
            membership_used == 0
            and membership_snapshot_json
            is not None
        ):
            _add_issue(
                issues,
                issue_identifier,
                "UNEXPECTED_MEMBERSHIP_SNAPSHOT",
                (
                    "membership_used is false "
                    "but a snapshot exists"
                ),
            )

        if (
            customer_snapshot
            is not None
            and customer_snapshot.get(
                "customer_id"
            )
            != customer_id
        ):
            _add_issue(
                issues,
                issue_identifier,
                "CUSTOMER_SNAPSHOT_MISMATCH",
                (
                    "customer snapshot identity "
                    "does not match audit record"
                ),
            )

        if ranked_actions is None:
            continue

        if not ranked_actions:
            _add_issue(
                issues,
                issue_identifier,
                "INCOMPLETE_RANKED_ACTIONS",
                "ranked action snapshot is empty",
            )
            continue

        ranked_actions_complete = True

        for action in ranked_actions:
            if not isinstance(
                action,
                dict,
            ):
                ranked_actions_complete = False
                break

            if not (
                REQUIRED_RANKED_ACTION_FIELDS
                .issubset(
                    action.keys()
                )
            ):
                ranked_actions_complete = False
                break

            if not isinstance(
                action["reason_codes"],
                list,
            ):
                ranked_actions_complete = False
                break

        if not ranked_actions_complete:
            _add_issue(
                issues,
                issue_identifier,
                "INCOMPLETE_RANKED_ACTIONS",
                (
                    "ranked action snapshot "
                    "is missing required fields"
                ),
            )
            continue

        winning_action = next(
            (
                action
                for action
                in ranked_actions
                if action[
                    "eligible"
                ] is True
            ),
            None,
        )

        if winning_action is None:
            _add_issue(
                issues,
                issue_identifier,
                "NO_ELIGIBLE_RANKED_ACTION",
                (
                    "ranked action snapshot "
                    "contains no eligible winner"
                ),
            )
            continue

        if (
            winning_action["action"]
            != selected_action
        ):
            _add_issue(
                issues,
                issue_identifier,
                "SELECTED_ACTION_MISMATCH",
                (
                    "selected_action does not "
                    "match ranked winner"
                ),
            )

        if (
            winning_action["score"]
            != selected_score
        ):
            _add_issue(
                issues,
                issue_identifier,
                "SELECTED_SCORE_MISMATCH",
                (
                    "selected_score does not "
                    "match ranked winner"
                ),
            )

        if (
            bool(
                selected_eligible
            )
            != winning_action[
                "eligible"
            ]
        ):
            _add_issue(
                issues,
                issue_identifier,
                "SELECTED_ELIGIBILITY_MISMATCH",
                (
                    "selected eligibility does "
                    "not match ranked winner"
                ),
            )

        if (
            selected_reason_codes
            is not None
            and selected_reason_codes
            != winning_action[
                "reason_codes"
            ]
        ):
            _add_issue(
                issues,
                issue_identifier,
                "SELECTED_REASON_CODES_MISMATCH",
                (
                    "selected reason codes do "
                    "not match ranked winner"
                ),
            )

    return issues