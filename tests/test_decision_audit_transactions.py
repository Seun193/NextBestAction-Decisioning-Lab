import sqlite3

import pytest
from fastapi.testclient import TestClient

import src.repository as repository_module

from src.app import app
from src.decision_audit import (
    persist_decision_audit,
)
from src.decision_audit_schema import (
    create_decision_audit_schema,
)
from src.membership_decisioning import (
    decide_with_membership,
)
from src.models import Customer


client = TestClient(app)


CUSTOMER_ID = "C00001"


def make_customer() -> Customer:
    return Customer(
        customer_id=CUSTOMER_ID,
        age=36,
        monthly_income=4500,
        savings_balance=18000,
        monthly_surplus=900,
        has_mortgage=False,
        has_credit_card=True,
        investment_customer=False,
        app_visits_30d=12,
        marketing_consent=True,
        investment_consent=True,
        credit_score_band="HIGH",
        preferred_channel="MOBILE",
    )


def create_audit_database():
    connection = sqlite3.connect(
        ":memory:"
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

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
            CUSTOMER_ID,
        ),
    )

    connection.commit()

    create_decision_audit_schema(
        connection
    )

    return connection


def install_failure_trigger(
    connection,
):
    connection.execute(
        """
        CREATE TRIGGER
            force_decision_audit_failure
        BEFORE INSERT
        ON decision_audits
        BEGIN
            SELECT RAISE(
                ABORT,
                'forced audit persistence failure'
            );
        END;
        """
    )

    connection.commit()


def create_real_api_database(
    database_path,
):
    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            """
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                age INTEGER NOT NULL,
                monthly_income REAL NOT NULL,
                savings_balance REAL NOT NULL,
                monthly_surplus REAL NOT NULL,
                has_mortgage INTEGER NOT NULL,
                has_credit_card INTEGER NOT NULL,
                investment_customer INTEGER NOT NULL,
                app_visits_30d INTEGER NOT NULL,
                marketing_consent INTEGER NOT NULL,
                investment_consent INTEGER NOT NULL,
                credit_score_band TEXT NOT NULL,
                preferred_channel TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            INSERT INTO customers (
                customer_id,
                age,
                monthly_income,
                savings_balance,
                monthly_surplus,
                has_mortgage,
                has_credit_card,
                investment_customer,
                app_visits_30d,
                marketing_consent,
                investment_consent,
                credit_score_band,
                preferred_channel
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                CUSTOMER_ID,
                36,
                4500.0,
                18000.0,
                900.0,
                0,
                1,
                0,
                12,
                1,
                1,
                "HIGH",
                "MOBILE",
            ),
        )

        connection.commit()

        create_decision_audit_schema(
            connection
        )

        install_failure_trigger(
            connection
        )


def test_failed_audit_insert_leaves_no_record():
    connection = create_audit_database()

    try:
        install_failure_trigger(
            connection
        )

        customer = make_customer()

        decision = decide_with_membership(
            customer,
            None,
        )

        with pytest.raises(
            sqlite3.IntegrityError,
            match=(
                "forced audit persistence failure"
            ),
        ):
            persist_decision_audit(
                connection,
                customer,
                None,
                decision,
                decision_id=(
                    "DEC-FORCED-FAILURE"
                ),
            )

        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM decision_audits
            """
        ).fetchone()[0]

        assert count == 0

    finally:
        connection.close()


def test_failed_write_preserves_existing_history():
    connection = create_audit_database()

    try:
        customer = make_customer()

        decision = decide_with_membership(
            customer,
            None,
        )

        persist_decision_audit(
            connection,
            customer,
            None,
            decision,
            decision_id="DEC-EXISTING",
        )

        install_failure_trigger(
            connection
        )

        with pytest.raises(
            sqlite3.IntegrityError
        ):
            persist_decision_audit(
                connection,
                customer,
                None,
                decision,
                decision_id="DEC-FAILED",
            )

        rows = connection.execute(
            """
            SELECT decision_id
            FROM decision_audits
            ORDER BY decision_id
            """
        ).fetchall()

        assert rows == [
            (
                "DEC-EXISTING",
            )
        ]

    finally:
        connection.close()


def test_trigger_side_effect_is_rolled_back_atomically():
    connection = create_audit_database()

    try:
        connection.execute(
            """
            CREATE TABLE audit_write_probe (
                marker TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TRIGGER
                force_atomic_failure
            BEFORE INSERT
            ON decision_audits
            BEGIN
                INSERT INTO audit_write_probe (
                    marker
                )
                VALUES (
                    'before-failure'
                );

                SELECT RAISE(
                    ABORT,
                    'forced atomic failure'
                );
            END;
            """
        )

        connection.commit()

        customer = make_customer()

        decision = decide_with_membership(
            customer,
            None,
        )

        with pytest.raises(
            sqlite3.IntegrityError,
            match="forced atomic failure",
        ):
            persist_decision_audit(
                connection,
                customer,
                None,
                decision,
                decision_id=(
                    "DEC-ATOMIC-FAILURE"
                ),
            )

        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM decision_audits
            """
        ).fetchone()[0]

        probe_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_write_probe
            """
        ).fetchone()[0]

        assert audit_count == 0
        assert probe_count == 0

    finally:
        connection.close()


def test_real_api_fails_closed_on_sqlite_failure(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "nba_forced_audit_failure.db"
    )

    create_real_api_database(
        database_path
    )

    monkeypatch.setattr(
        repository_module,
        "DB_FILE",
        database_path,
    )

    response = client.get(
        f"/nba/{CUSTOMER_ID}"
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": (
            "Decision audit "
            "persistence failed"
        )
    }

    assert (
        "x-decision-id"
        not in response.headers
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM decision_audits
            """
        ).fetchone()[0]

    assert audit_count == 0