import sqlite3


OUTCOME_TABLE = "decision_outcomes"
OUTCOME_SCHEMA_VERSION = "1.0"

SUPPORTED_EVENT_TYPES = {
    "VIEWED",
    "CLICKED",
    "ACCEPTED",
    "DISMISSED",
    "CONVERTED",
}

REQUIRED_COLUMNS = {
    "outcome_event_id",
    "decision_id",
    "customer_id",
    "selected_action",
    "event_type",
    "event_timestamp",
    "received_timestamp",
    "event_source",
    "conversion_value",
    "conversion_currency",
    "metadata_json",
    "outcome_schema_version",
}


def create_decision_outcome_schema(
    connection: sqlite3.Connection,
) -> None:
    """
    Create the Decision Outcome and Feedback schema.

    Existing audit and outcome history is preserved.
    Re-running schema creation is safe.
    """

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS decision_outcomes (
            outcome_event_id TEXT PRIMARY KEY,

            decision_id TEXT NOT NULL,

            customer_id TEXT NOT NULL,

            selected_action TEXT NOT NULL,

            event_type TEXT NOT NULL
                CHECK (
                    event_type IN (
                        'VIEWED',
                        'CLICKED',
                        'ACCEPTED',
                        'DISMISSED',
                        'CONVERTED'
                    )
                ),

            event_timestamp TEXT NOT NULL,

            received_timestamp TEXT NOT NULL,

            event_source TEXT NOT NULL,

            conversion_value REAL
                CHECK (
                    conversion_value IS NULL
                    OR conversion_value >= 0.0
                ),

            conversion_currency TEXT,

            metadata_json TEXT,

            outcome_schema_version TEXT NOT NULL,

            FOREIGN KEY (decision_id)
                REFERENCES decision_audits(decision_id),

            CHECK (
                (
                    event_type = 'CONVERTED'
                    AND (
                        (
                            conversion_value IS NULL
                            AND conversion_currency IS NULL
                        )
                        OR
                        (
                            conversion_value IS NOT NULL
                            AND conversion_currency IS NOT NULL
                        )
                    )
                )
                OR
                (
                    event_type <> 'CONVERTED'
                    AND conversion_value IS NULL
                    AND conversion_currency IS NULL
                )
            )
        );


        CREATE INDEX IF NOT EXISTS
            idx_decision_outcomes_decision_id
        ON decision_outcomes(decision_id);


        CREATE INDEX IF NOT EXISTS
            idx_decision_outcomes_customer_id
        ON decision_outcomes(customer_id);


        CREATE INDEX IF NOT EXISTS
            idx_decision_outcomes_event_type
        ON decision_outcomes(event_type);


        CREATE INDEX IF NOT EXISTS
            idx_decision_outcomes_event_timestamp
        ON decision_outcomes(event_timestamp);


        CREATE INDEX IF NOT EXISTS
            idx_decision_outcomes_selected_action
        ON decision_outcomes(selected_action);
        """
    )

    connection.commit()


def validate_decision_audit_table(
    connection: sqlite3.Connection,
) -> None:
    """
    Outcome records depend on the existing decision_audits table.
    """

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'decision_audits'
        """
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "decision_audits table not found"
        )


def verify_decision_outcome_schema(
    connection: sqlite3.Connection,
) -> None:
    """
    Verify that the outcome table and required columns exist,
    and that SQLite foreign-key enforcement is active.
    """

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (
            OUTCOME_TABLE,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "decision_outcomes table not found"
        )

    columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(decision_outcomes)
            """
        ).fetchall()
    }

    missing_columns = (
        REQUIRED_COLUMNS - columns
    )

    if missing_columns:
        raise RuntimeError(
            "Decision outcome schema verification failed. "
            f"Missing columns: {sorted(missing_columns)}"
        )

    foreign_keys_enabled = (
        connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
    )

    if foreign_keys_enabled != 1:
        raise RuntimeError(
            "SQLite foreign-key enforcement "
            "is not enabled."
        )