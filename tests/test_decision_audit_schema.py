import sqlite3

import pytest

from src.decision_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    AUDIT_TABLE,
    REQUIRED_COLUMNS,
    create_decision_audit_schema,
    validate_customer_table,
    verify_decision_audit_schema,
)


def create_customer_table(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY
        )
        """
    )

    connection.execute(
        """
        INSERT INTO customers (
            customer_id
        )
        VALUES (?)
        """,
        (
            "C00001",
        ),
    )

    connection.commit()


def insert_valid_audit(
    connection: sqlite3.Connection,
    decision_id: str = "DEC-001",
) -> None:
    connection.execute(
        """
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
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            decision_id,
            "C00001",
            "2026-09-30T12:00:00Z",
            "SAVINGS_PLAN",
            0.52,
            1,
            '["MONTHLY_SURPLUS"]',
            '[{"action":"SAVINGS_PLAN","score":0.52}]',
            '{"customer_id":"C00001"}',
            None,
            0,
            "decision-engine-v1",
            None,
            "1.0.0",
            AUDIT_SCHEMA_VERSION,
        ),
    )

    connection.commit()


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    create_customer_table(conn)

    yield conn

    conn.close()


def test_schema_creates_decision_audit_table(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (
            AUDIT_TABLE,
        ),
    ).fetchone()

    assert row is not None


def test_schema_contains_required_columns(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(decision_audits)
            """
        ).fetchall()
    }

    assert REQUIRED_COLUMNS.issubset(
        columns
    )


def test_schema_creation_is_reload_safe(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    insert_valid_audit(
        connection
    )

    create_decision_audit_schema(
        connection
    )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_audits
        """
    ).fetchone()[0]

    assert count == 1


def test_decision_id_must_be_unique(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    insert_valid_audit(
        connection,
        decision_id="DEC-001",
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_audit(
            connection,
            decision_id="DEC-001",
        )


def test_audit_requires_valid_customer(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        connection.execute(
            """
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "DEC-INVALID-CUSTOMER",
                "C99999",
                "2026-09-30T12:00:00Z",
                "SAVINGS_PLAN",
                0.52,
                1,
                "[]",
                "[]",
                "{}",
                None,
                0,
                "decision-engine-v1",
                None,
                "1.0.0",
                AUDIT_SCHEMA_VERSION,
            ),
        )


def test_selected_eligible_must_be_boolean_style(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        connection.execute(
            """
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "DEC-BAD-ELIGIBLE",
                "C00001",
                "2026-09-30T12:00:00Z",
                "SAVINGS_PLAN",
                0.52,
                2,
                "[]",
                "[]",
                "{}",
                None,
                0,
                "decision-engine-v1",
                None,
                "1.0.0",
                AUDIT_SCHEMA_VERSION,
            ),
        )


def test_membership_used_must_be_boolean_style(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        connection.execute(
            """
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "DEC-BAD-MEMBERSHIP",
                "C00001",
                "2026-09-30T12:00:00Z",
                "SAVINGS_PLAN",
                0.52,
                1,
                "[]",
                "[]",
                "{}",
                None,
                4,
                "decision-engine-v1",
                None,
                "1.0.0",
                AUDIT_SCHEMA_VERSION,
            ),
        )


@pytest.mark.parametrize(
    "score",
    [
        -0.01,
        1.01,
    ],
)
def test_selected_score_must_be_in_range(
    connection,
    score,
):
    create_decision_audit_schema(
        connection
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        connection.execute(
            """
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "DEC-BAD-SCORE",
                "C00001",
                "2026-09-30T12:00:00Z",
                "SAVINGS_PLAN",
                score,
                1,
                "[]",
                "[]",
                "{}",
                None,
                0,
                "decision-engine-v1",
                None,
                "1.0.0",
                AUDIT_SCHEMA_VERSION,
            ),
        )


def test_validate_customer_table_fails_without_customers():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="customers table not found",
        ):
            validate_customer_table(
                connection
            )
    finally:
        connection.close()


def test_verify_schema_passes_for_valid_schema(
    connection,
):
    create_decision_audit_schema(
        connection
    )

    verify_decision_audit_schema(
        connection
    )


def test_verify_schema_fails_when_table_missing():
    connection = sqlite3.connect(
        ":memory:"
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    create_customer_table(
        connection
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="decision_audits table not found",
        ):
            verify_decision_audit_schema(
                connection
            )
    finally:
        connection.close()