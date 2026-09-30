import sqlite3

import pytest

from src.decision_audit import (
    API_VERSION,
    DECISION_ENGINE_VERSION,
    get_decision_audit,
    persist_decision_audit,
)
from src.decision_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    create_decision_audit_schema,
)
from src.membership_decisioning import (
    decide_with_membership,
)
from src.models import (
    Customer,
    MembershipContext,
    NBAResponse,
)


def make_customer() -> Customer:
    return Customer(
        customer_id="C00001",
        age=35,
        monthly_income=5000,
        savings_balance=20000,
        monthly_surplus=700,
        has_mortgage=True,
        has_credit_card=True,
        investment_customer=False,
        app_visits_30d=10,
        marketing_consent=True,
        investment_consent=True,
        credit_score_band="HIGH",
        preferred_channel="MOBILE",
    )


def make_membership() -> MembershipContext:
    return MembershipContext(
        member_id="M00001",
        membership_status="ACTIVE",
        membership_tier="PLUS",
        tenure_days=400,
        engagement_events_30d=8,
        successful_benefit_redemptions_30d=2,
        campaign_sends_30d=3,
        campaign_conversions_30d=1,
        latest_campaign_response="CONVERTED",
    )


@pytest.fixture
def connection():
    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    conn.execute(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY
        )
        """
    )

    conn.execute(
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

    conn.commit()

    create_decision_audit_schema(
        conn
    )

    yield conn

    conn.close()


def test_persist_and_retrieve_non_member_decision(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    decision_id = persist_decision_audit(
        connection,
        customer,
        None,
        decision,
        decision_timestamp=(
            "2026-09-30T12:30:00Z"
        ),
    )

    record = get_decision_audit(
        connection,
        decision_id,
    )

    assert record is not None

    assert record.decision_id.startswith(
        "DEC-"
    )

    assert (
        record.customer_id
        == customer.customer_id
    )

    assert (
        record.selected_action
        == decision.next_best_action
    )

    assert (
        record.selected_score
        == decision.score
    )

    assert (
        record.selected_eligible
        == decision.eligible
    )

    assert (
        record.selected_reason_codes
        == decision.reason_codes
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
        == "C00001"
    )


def test_member_decision_preserves_membership_context(
    connection,
):
    customer = make_customer()
    membership = make_membership()

    decision = decide_with_membership(
        customer,
        membership,
    )

    decision_id = persist_decision_audit(
        connection,
        customer,
        membership,
        decision,
    )

    record = get_decision_audit(
        connection,
        decision_id,
    )

    assert record is not None

    assert (
        record.membership_used
        is True
    )

    assert (
        record.membership_snapshot[
            "member_id"
        ]
        == "M00001"
    )

    assert (
        record.membership_snapshot[
            "membership_status"
        ]
        == "ACTIVE"
    )

    assert (
        "MEMBERSHIP_RECENT_ENGAGEMENT"
        in record.selected_reason_codes
    )

    assert (
        "MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION"
        in record.selected_reason_codes
    )


def test_ranked_actions_round_trip_exactly(
    connection,
):
    customer = make_customer()
    membership = make_membership()

    decision = decide_with_membership(
        customer,
        membership,
    )

    decision_id = persist_decision_audit(
        connection,
        customer,
        membership,
        decision,
    )

    record = get_decision_audit(
        connection,
        decision_id,
    )

    assert record is not None

    assert len(
        record.ranked_actions
    ) == len(
        decision.ranked_actions
    )

    for stored, original in zip(
        record.ranked_actions,
        decision.ranked_actions,
    ):
        assert (
            stored["action"]
            == original.action
        )

        assert (
            stored["score"]
            == original.score
        )

        assert (
            stored["eligible"]
            == original.eligible
        )

        assert (
            stored["reason_codes"]
            == original.reason_codes
        )


def test_repeated_decisions_are_append_only(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    first_id = persist_decision_audit(
        connection,
        customer,
        None,
        decision,
    )

    second_id = persist_decision_audit(
        connection,
        customer,
        None,
        decision,
    )

    assert first_id != second_id

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_audits
        WHERE customer_id = ?
        """,
        (
            customer.customer_id,
        ),
    ).fetchone()[0]

    assert count == 2


def test_customer_snapshot_is_historical(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    decision_id = persist_decision_audit(
        connection,
        customer,
        None,
        decision,
    )

    original_income = (
        customer.monthly_income
    )

    customer.monthly_income = 9999

    record = get_decision_audit(
        connection,
        decision_id,
    )

    assert record is not None

    assert (
        record.customer_snapshot[
            "monthly_income"
        ]
        == original_income
    )

    assert (
        record.customer_snapshot[
            "monthly_income"
        ]
        != customer.monthly_income
    )


def test_missing_decision_returns_none(
    connection,
):
    record = get_decision_audit(
        connection,
        "DEC-DOES-NOT-EXIST",
    )

    assert record is None


def test_customer_decision_identity_mismatch_is_rejected(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    mismatched = NBAResponse(
        customer_id="C99999",
        next_best_action=(
            decision.next_best_action
        ),
        score=decision.score,
        eligible=decision.eligible,
        reason_codes=(
            decision.reason_codes
        ),
        ranked_actions=(
            decision.ranked_actions
        ),
    )

    with pytest.raises(
        ValueError,
        match="customer_id",
    ):
        persist_decision_audit(
            connection,
            customer,
            None,
            mismatched,
        )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_audits
        """
    ).fetchone()[0]

    assert count == 0


def test_selected_action_must_match_ranked_winner(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    inconsistent = NBAResponse(
        customer_id=(
            decision.customer_id
        ),
        next_best_action=(
            "SAVINGS_PLAN"
        ),
        score=decision.score,
        eligible=decision.eligible,
        reason_codes=(
            decision.reason_codes
        ),
        ranked_actions=(
            decision.ranked_actions
        ),
    )

    with pytest.raises(
        ValueError,
        match="Selected action",
    ):
        persist_decision_audit(
            connection,
            customer,
            None,
            inconsistent,
        )


def test_versions_and_explicit_identity_are_preserved(
    connection,
):
    customer = make_customer()

    decision = decide_with_membership(
        customer,
        None,
    )

    decision_id = persist_decision_audit(
        connection,
        customer,
        None,
        decision,
        decision_id="DEC-FIXED-001",
        decision_timestamp=(
            "2026-09-30T13:00:00Z"
        ),
        decision_engine_version=(
            "decision-engine-test"
        ),
        model_version=(
            "model-test-v7"
        ),
        api_version="9.9.9",
    )

    record = get_decision_audit(
        connection,
        decision_id,
    )

    assert record is not None

    assert (
        record.decision_id
        == "DEC-FIXED-001"
    )

    assert (
        record.decision_timestamp
        == "2026-09-30T13:00:00Z"
    )

    assert (
        record.decision_engine_version
        == "decision-engine-test"
    )

    assert (
        record.model_version
        == "model-test-v7"
    )

    assert (
        record.api_version
        == "9.9.9"
    )

    assert (
        record.audit_schema_version
        == AUDIT_SCHEMA_VERSION
    )


def test_duplicate_decision_id_is_rejected(
    connection,
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
        decision_id="DEC-DUPLICATE",
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        persist_decision_audit(
            connection,
            customer,
            None,
            decision,
            decision_id="DEC-DUPLICATE",
        )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM decision_audits
        """
    ).fetchone()[0]

    assert count == 1