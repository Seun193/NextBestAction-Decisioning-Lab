import sqlite3

from src.decision_audit import (
    persist_decision_audit,
)
from src.decision_audit_quality import (
    count_decision_audits,
    validate_decision_audit_quality,
)
from src.decision_audit_schema import (
    create_decision_audit_schema,
)
from src.membership_decisioning import (
    decide_with_membership,
)
from src.models import Customer


def make_customer() -> Customer:
    return Customer(
        customer_id="C00001",
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


def create_valid_database():
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
        VALUES ('C00001')
        """
    )

    connection.commit()

    create_decision_audit_schema(
        connection
    )

    return connection


def persist_valid_decision(
    connection,
    decision_id="DEC-QUALITY-001",
):
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
        decision_id=decision_id,
        decision_timestamp=(
            "2026-09-30T15:00:00Z"
        ),
    )

    return decision


def issue_codes(
    connection,
):
    return {
        issue.code
        for issue
        in validate_decision_audit_quality(
            connection
        )
    }


def create_relaxed_audit_table(
    connection,
):
    connection.execute(
        """
        CREATE TABLE decision_audits (
            decision_id TEXT,
            customer_id TEXT,
            decision_timestamp TEXT,
            selected_action TEXT,
            selected_score REAL,
            selected_eligible INTEGER,
            selected_reason_codes_json TEXT,
            ranked_actions_json TEXT,
            customer_snapshot_json TEXT,
            membership_snapshot_json TEXT,
            membership_used INTEGER,
            decision_engine_version TEXT,
            model_version TEXT,
            api_version TEXT,
            audit_schema_version TEXT
        )
        """
    )


def insert_relaxed_valid_row(
    connection,
    decision_id,
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
            decision_id,
            "C00001",
            "2026-09-30T15:00:00Z",
            "SAVINGS_PLAN",
            0.5,
            1,
            '["TEST_REASON"]',
            (
                '[{"action":"SAVINGS_PLAN",'
                '"score":0.5,'
                '"eligible":true,'
                '"reason_codes":["TEST_REASON"]}]'
            ),
            '{"customer_id":"C00001"}',
            None,
            0,
            "decision-engine-v1",
            None,
            "1.0.0",
            "1.0",
        ),
    )

    connection.commit()


def test_valid_audit_has_no_quality_issues():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        issues = (
            validate_decision_audit_quality(
                connection
            )
        )

        assert issues == []

    finally:
        connection.close()


def test_invalid_reason_codes_json_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET selected_reason_codes_json =
                'not-json'
            """
        )

        connection.commit()

        assert (
            "INVALID_SERIALIZED_FIELD"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_invalid_ranked_actions_json_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET ranked_actions_json =
                'not-json'
            """
        )

        connection.commit()

        assert (
            "INVALID_SERIALIZED_FIELD"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_incomplete_ranked_action_snapshot_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET ranked_actions_json =
                '[{"action":"SAVINGS_PLAN"}]'
            """
        )

        connection.commit()

        assert (
            "INCOMPLETE_RANKED_ACTIONS"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_selected_action_inconsistency_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET selected_action =
                'ALTERED_ACTION'
            """
        )

        connection.commit()

        assert (
            "SELECTED_ACTION_MISMATCH"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_selected_score_inconsistency_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET selected_score = 0.01
            """
        )

        connection.commit()

        assert (
            "SELECTED_SCORE_MISMATCH"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_selected_reason_code_inconsistency_is_detected():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection
        )

        connection.execute(
            """
            UPDATE decision_audits
            SET selected_reason_codes_json =
                '["ALTERED_REASON"]'
            """
        )

        connection.commit()

        assert (
            "SELECTED_REASON_CODES_MISMATCH"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_missing_identifiers_and_action_are_detected():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        create_relaxed_audit_table(
            connection
        )

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
                " ",
                "",
                "2026-09-30T15:00:00Z",
                None,
                0.5,
                1,
                "[]",
                (
                    '[{"action":"SAVINGS_PLAN",'
                    '"score":0.5,'
                    '"eligible":true,'
                    '"reason_codes":[]}]'
                ),
                '{"customer_id":""}',
                None,
                0,
                "decision-engine-v1",
                None,
                "1.0.0",
                "1.0",
            ),
        )

        connection.commit()

        codes = issue_codes(
            connection
        )

        assert (
            "MISSING_DECISION_ID"
            in codes
        )

        assert (
            "MISSING_CUSTOMER_ID"
            in codes
        )

        assert (
            "MISSING_SELECTED_ACTION"
            in codes
        )

    finally:
        connection.close()


def test_duplicate_decision_identifier_is_detected():
    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        create_relaxed_audit_table(
            connection
        )

        insert_relaxed_valid_row(
            connection,
            "DEC-DUPLICATE",
        )

        insert_relaxed_valid_row(
            connection,
            "DEC-DUPLICATE",
        )

        assert (
            "DUPLICATE_DECISION_ID"
            in issue_codes(
                connection
            )
        )

    finally:
        connection.close()


def test_record_count_helper_reports_exact_count():
    connection = create_valid_database()

    try:
        persist_valid_decision(
            connection,
            "DEC-COUNT-001",
        )

        persist_valid_decision(
            connection,
            "DEC-COUNT-002",
        )

        assert (
            count_decision_audits(
                connection
            )
            == 2
        )

    finally:
        connection.close()