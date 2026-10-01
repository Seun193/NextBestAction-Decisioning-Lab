import sqlite3


AUDIT_TABLE = "decision_audits"
AUDIT_SCHEMA_VERSION = "1.0"


REQUIRED_COLUMNS = {
    "decision_id",
    "customer_id",
    "decision_timestamp",
    "selected_action",
    "selected_score",
    "selected_eligible",
    "selected_reason_codes_json",
    "ranked_actions_json",
    "customer_snapshot_json",
    "membership_snapshot_json",
    "membership_used",
    "decision_engine_version",
    "model_version",
    "api_version",
    "audit_schema_version",
}


def create_decision_audit_schema(
    connection: sqlite3.Connection,
) -> None:
    """
    Create the Decision Audit and Traceability schema.

    Existing customer and decision-audit data is preserved.
    Re-running schema creation is safe.
    """

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS decision_audits (
            decision_id TEXT PRIMARY KEY,

            customer_id TEXT NOT NULL,

            decision_timestamp TEXT NOT NULL,

            selected_action TEXT NOT NULL,

            selected_score REAL NOT NULL
                CHECK (
                    selected_score >= 0.0
                    AND selected_score <= 1.0
                ),

            selected_eligible INTEGER NOT NULL
                CHECK (
                    selected_eligible IN (0, 1)
                ),

            selected_reason_codes_json TEXT NOT NULL,

            ranked_actions_json TEXT NOT NULL,

            customer_snapshot_json TEXT NOT NULL,

            membership_snapshot_json TEXT,

            membership_used INTEGER NOT NULL
                CHECK (
                    membership_used IN (0, 1)
                ),

            decision_engine_version TEXT NOT NULL,

            model_version TEXT,

            api_version TEXT NOT NULL,

            audit_schema_version TEXT NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
        );


        CREATE INDEX IF NOT EXISTS
            idx_decision_audits_customer_id
        ON decision_audits(customer_id);


        CREATE INDEX IF NOT EXISTS
            idx_decision_audits_timestamp
        ON decision_audits(decision_timestamp);


        CREATE INDEX IF NOT EXISTS
            idx_decision_audits_action
        ON decision_audits(selected_action);
        """
    )

    connection.commit()


def validate_customer_table(
    connection: sqlite3.Connection,
) -> None:
    """
    Decision audit records depend on the existing customers table.
    """

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'customers'
        """
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "customers table not found"
        )


def verify_decision_audit_schema(
    connection: sqlite3.Connection,
) -> None:
    """
    Verify that the decision audit table and required columns exist,
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
            AUDIT_TABLE,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "decision_audits table not found"
        )

    columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(decision_audits)
            """
        ).fetchall()
    }

    missing_columns = (
        REQUIRED_COLUMNS - columns
    )

    if missing_columns:
        raise RuntimeError(
            "Decision audit schema verification failed. "
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