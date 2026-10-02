import sqlite3

import pytest

from src.decision_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    create_decision_audit_schema,
)
from src.decision_outcome_schema import (
    OUTCOME_SCHEMA_VERSION,
    OUTCOME_TABLE,
    REQUIRED_COLUMNS,
    SUPPORTED_EVENT_TYPES,
    create_decision_outcome_schema,
    validate_decision_audit_table,
    verify_decision_outcome_schema,
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
        ("C00001",),
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
            "2026-10-01T12:00:00Z",
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


def insert_valid_outcome(
    connection: sqlite3.Connection,
    outcome_event_id: str = "OUT-001",
    decision_id: str = "DEC-001",
    event_type: str = "VIEWED",
    conversion_value=None,
    conversion_currency=None,
) -> None:
    connection.execute(
        """
        INSERT INTO decision_outcomes (
            outcome_event_id,
            decision_id,
            customer_id,
            selected_action,
            event_type,
            event_timestamp,
            received_timestamp,
            event_source,
            conversion_value,
            conversion_currency,
            metadata_json,
            outcome_schema_version
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            outcome_event_id,
            decision_id,
            "C00001",
            "SAVINGS_PLAN",
            event_type,
            "2026-10-01T12:05:00Z",
            "2026-10-01T12:05:01Z",
            "SYNTHETIC_TEST",
            conversion_value,
            conversion_currency,
            '{"channel":"test"}',
            OUTCOME_SCHEMA_VERSION,
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
    create_decision_audit_schema(conn)
    insert_valid_audit(conn)
    create_decision_outcome_schema(conn)

    yield conn

    conn.close()


def test_schema_creates_decision_outcome_table(
    connection,
):
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (OUTCOME_TABLE,),
    ).fetchone()

    assert row is not None


def test_schema_contains_required_columns(
    connection,
):
    columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(decision_outcomes)
            """
        ).fetchall()
    }

    assert REQUIRED_COLUMNS.issubset(
        columns
    )


def test_schema_verification_passes(
    connection,
):
    verify_decision_outcome_schema(
        connection
    )


def test_supported_event_types_are_defined():
    assert SUPPORTED_EVENT_TYPES == {
        "VIEWED",
        "CLICKED",
        "ACCEPTED",
        "DISMISSED",
        "CONVERTED",
    }


def test_schema_creation_is_reload_safe(
    connection,
):
    insert_valid_outcome(connection)

    create_decision_outcome_schema(
        connection
    )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_outcomes
        """
    ).fetchone()[0]

    assert count == 1


def test_outcome_event_id_must_be_unique(
    connection,
):
    insert_valid_outcome(
        connection,
        outcome_event_id="OUT-001",
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-001",
        )


def test_outcome_requires_existing_decision(
    connection,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-UNKNOWN",
            decision_id="DEC-DOES-NOT-EXIST",
        )


@pytest.mark.parametrize(
    "event_type",
    [
        "VIEWED",
        "CLICKED",
        "ACCEPTED",
        "DISMISSED",
        "CONVERTED",
    ],
)
def test_supported_event_types_are_accepted(
    connection,
    event_type,
):
    insert_valid_outcome(
        connection,
        outcome_event_id=f"OUT-{event_type}",
        event_type=event_type,
    )


def test_unsupported_event_type_is_rejected(
    connection,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-INVALID",
            event_type="PURCHASED",
        )


def test_negative_conversion_value_is_rejected(
    connection,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-NEGATIVE",
            event_type="CONVERTED",
            conversion_value=-1.0,
            conversion_currency="EUR",
        )


def test_converted_event_accepts_value_and_currency(
    connection,
):
    insert_valid_outcome(
        connection,
        outcome_event_id="OUT-CONVERTED",
        event_type="CONVERTED",
        conversion_value=125.50,
        conversion_currency="EUR",
    )

    row = connection.execute(
        """
        SELECT
            conversion_value,
            conversion_currency
        FROM decision_outcomes
        WHERE outcome_event_id = ?
        """,
        ("OUT-CONVERTED",),
    ).fetchone()

    assert row == (
        125.50,
        "EUR",
    )


def test_converted_event_rejects_value_without_currency(
    connection,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-NO-CURRENCY",
            event_type="CONVERTED",
            conversion_value=50.0,
            conversion_currency=None,
        )


def test_converted_event_rejects_currency_without_value(
    connection,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id="OUT-NO-VALUE",
            event_type="CONVERTED",
            conversion_value=None,
            conversion_currency="EUR",
        )


def test_converted_event_may_have_no_recorded_value(
    connection,
):
    insert_valid_outcome(
        connection,
        outcome_event_id="OUT-CONVERSION-NO-VALUE",
        event_type="CONVERTED",
        conversion_value=None,
        conversion_currency=None,
    )


@pytest.mark.parametrize(
    "event_type",
    [
        "VIEWED",
        "CLICKED",
        "ACCEPTED",
        "DISMISSED",
    ],
)
def test_non_conversion_event_rejects_conversion_value(
    connection,
    event_type,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        insert_valid_outcome(
            connection,
            outcome_event_id=f"OUT-VALUE-{event_type}",
            event_type=event_type,
            conversion_value=10.0,
            conversion_currency="EUR",
        )


def test_validate_decision_audit_table_passes(
    connection,
):
    validate_decision_audit_table(
        connection
    )


def test_validate_decision_audit_table_fails_when_missing():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="decision_audits table not found",
        ):
            validate_decision_audit_table(
                connection
            )
    finally:
        connection.close()


def test_schema_verification_requires_foreign_keys(
    connection,
):
    connection.execute(
        "PRAGMA foreign_keys = OFF"
    )

    with pytest.raises(
        RuntimeError,
        match="foreign-key enforcement",
    ):
        verify_decision_outcome_schema(
            connection
        )