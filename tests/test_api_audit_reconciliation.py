import sqlite3

from fastapi.testclient import TestClient

import src.repository as repository_module
from src.app import app
from src.decision_audit import (
    get_decision_audit,
)
from src.membership_schema import (
    create_membership_schema,
)


client = TestClient(app)


CUSTOMER_ID = "C00001"


def create_customer_database(
    database_path,
) -> None:
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


def add_membership_data(
    database_path,
) -> None:
    with sqlite3.connect(
        database_path
    ) as connection:
        create_membership_schema(
            connection
        )

        connection.execute(
            """
            INSERT INTO members (
                member_id,
                customer_id,
                membership_status,
                membership_tier,
                join_date,
                end_date,
                marketing_consent,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "M000001",
                CUSTOMER_ID,
                "ACTIVE",
                "PLUS",
                "2025-01-01",
                None,
                1,
                "2025-01-01T00:00:00",
                "2026-09-21T00:00:00",
            ),
        )

        engagement_rows = [
            (
                f"E{i:03d}",
                "M000001",
                "APP_LOGIN",
                f"2026-09-{10 + i:02d}T10:00:00",
                "MOBILE",
            )
            for i in range(
                1,
                6,
            )
        ]

        connection.executemany(
            """
            INSERT INTO engagement_events (
                event_id,
                member_id,
                event_type,
                event_timestamp,
                channel
            )
            VALUES (
                ?, ?, ?, ?, ?
            )
            """,
            engagement_rows,
        )

        connection.execute(
            """
            INSERT INTO campaign_interactions (
                interaction_id,
                campaign_id,
                member_id,
                channel,
                sent_timestamp,
                response_type,
                response_timestamp
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "I000001",
                "CMP001",
                "M000001",
                "EMAIL",
                "2026-09-18T09:00:00",
                "CONVERTED",
                "2026-09-18T11:00:00",
            ),
        )

        connection.commit()


def test_api_response_reconciles_to_real_audit_record(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "nba_audit_reconciliation.db"
    )

    create_customer_database(
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

    assert response.status_code == 200

    body = response.json()

    decision_id = response.headers[
        "x-decision-id"
    ]

    assert decision_id.startswith(
        "DEC-"
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        record = get_decision_audit(
            connection,
            decision_id,
        )

        row_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM decision_audits
            """
        ).fetchone()[0]

    assert row_count == 1
    assert record is not None

    assert (
        record.customer_id
        == body["customer_id"]
    )

    assert (
        record.selected_action
        == body["next_best_action"]
    )

    assert (
        record.selected_score
        == body["score"]
    )

    assert (
        record.selected_eligible
        == body["eligible"]
    )

    assert (
        record.selected_reason_codes
        == body["reason_codes"]
    )

    assert (
        record.ranked_actions
        == body["ranked_actions"]
    )

    assert (
        record.membership_used
        is False
    )

    assert (
        record.membership_snapshot
        is None
    )

    assert (
        record.customer_snapshot[
            "customer_id"
        ]
        == CUSTOMER_ID
    )

    assert (
        record.customer_snapshot[
            "monthly_income"
        ]
        == 4500.0
    )

    assert (
        record.customer_snapshot[
            "marketing_consent"
        ]
        is True
    )

    assert (
        record.model_version
        is None
    )


def test_member_api_response_reconciles_membership_audit(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "nba_member_audit.db"
    )

    create_customer_database(
        database_path
    )

    add_membership_data(
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

    assert response.status_code == 200

    body = response.json()

    decision_id = response.headers[
        "x-decision-id"
    ]

    with sqlite3.connect(
        database_path
    ) as connection:
        record = get_decision_audit(
            connection,
            decision_id,
        )

    assert record is not None

    assert (
        body["next_best_action"]
        == "INVESTMENT_INFO"
    )

    assert body["score"] == 0.93

    assert (
        record.selected_action
        == body["next_best_action"]
    )

    assert (
        record.selected_score
        == body["score"]
    )

    assert (
        record.selected_reason_codes
        == body["reason_codes"]
    )

    assert (
        record.ranked_actions
        == body["ranked_actions"]
    )

    assert (
        record.membership_used
        is True
    )

    assert (
        record.membership_snapshot
        is not None
    )

    assert (
        record.membership_snapshot[
            "member_id"
        ]
        == "M000001"
    )

    assert (
        record.membership_snapshot[
            "membership_status"
        ]
        == "ACTIVE"
    )

    assert (
        record.membership_snapshot[
            "membership_tier"
        ]
        == "PLUS"
    )

    assert (
        record.membership_snapshot[
            "engagement_events_30d"
        ]
        == 5
    )

    assert (
        record.membership_snapshot[
            "campaign_sends_30d"
        ]
        == 1
    )

    assert (
        record.membership_snapshot[
            "campaign_conversions_30d"
        ]
        == 1
    )

    assert (
        record.membership_snapshot[
            "latest_campaign_response"
        ]
        == "CONVERTED"
    )

    assert (
        "MEMBERSHIP_RECENT_ENGAGEMENT"
        in record.selected_reason_codes
    )

    assert (
        "MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION"
        in record.selected_reason_codes
    )


def test_repeated_api_requests_create_distinct_audit_records(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "nba_repeat_audit.db"
    )

    create_customer_database(
        database_path
    )

    monkeypatch.setattr(
        repository_module,
        "DB_FILE",
        database_path,
    )

    first_response = client.get(
        f"/nba/{CUSTOMER_ID}"
    )

    second_response = client.get(
        f"/nba/{CUSTOMER_ID}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_id = first_response.headers[
        "x-decision-id"
    ]

    second_id = second_response.headers[
        "x-decision-id"
    ]

    assert first_id != second_id

    with sqlite3.connect(
        database_path
    ) as connection:
        rows = connection.execute(
            """
            SELECT decision_id
            FROM decision_audits
            WHERE customer_id = ?
            ORDER BY decision_timestamp
            """,
            (
                CUSTOMER_ID,
            ),
        ).fetchall()

    assert len(rows) == 2

    stored_ids = {
        row[0]
        for row in rows
    }

    assert stored_ids == {
        first_id,
        second_id,
    }