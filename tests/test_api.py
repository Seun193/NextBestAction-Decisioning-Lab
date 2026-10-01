from fastapi.testclient import (
    TestClient,
)

import src.app as app_module

from src.models import (
    Customer,
    MembershipContext,
)


client = TestClient(
    app_module.app
)


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


def make_membership() -> MembershipContext:
    return MembershipContext(
        member_id="M000001",
        membership_status="ACTIVE",
        membership_tier="PLUS",
        tenure_days=500,
        engagement_events_30d=8,
        successful_benefit_redemptions_30d=2,
        campaign_sends_30d=3,
        campaign_conversions_30d=1,
        latest_campaign_response="CONVERTED",
    )


def test_health():
    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert (
        response.json()["status"]
        == "ok"
    )

    assert (
        response.json()["version"]
        == app_module.APP_VERSION
    )


def test_unknown_customer_returns_404(
    monkeypatch,
):
    audit_calls = []

    monkeypatch.setattr(
        app_module,
        "get_customer",
        lambda customer_id: None,
    )

    monkeypatch.setattr(
        app_module,
        "persist_api_decision",
        lambda *args: audit_calls.append(
            args
        ),
    )

    response = client.get(
        "/nba/C99999"
    )

    assert response.status_code == 404

    assert audit_calls == []

    assert (
        "x-decision-id"
        not in response.headers
    )


def test_non_member_uses_base_nba_decision(
    monkeypatch,
):
    customer = make_customer()

    monkeypatch.setattr(
        app_module,
        "get_customer",
        lambda customer_id: customer,
    )

    monkeypatch.setattr(
        app_module,
        "get_membership_context",
        lambda customer_id: None,
    )

    monkeypatch.setattr(
        app_module,
        "persist_api_decision",
        lambda customer, membership, decision:
            "DEC-NON-MEMBER-001",
    )

    response = client.get(
        "/nba/C00001"
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["customer_id"]
        == "C00001"
    )

    assert (
        body["next_best_action"]
        == "MORTGAGE_CONSULTATION"
    )

    assert body["score"] == 0.88

    assert (
        response.headers[
            "x-decision-id"
        ]
        == "DEC-NON-MEMBER-001"
    )

    assert "decision_id" not in body


def test_active_member_uses_membership_aware_ranking(
    monkeypatch,
):
    customer = make_customer()

    membership = make_membership()

    monkeypatch.setattr(
        app_module,
        "get_customer",
        lambda customer_id: customer,
    )

    monkeypatch.setattr(
        app_module,
        "get_membership_context",
        lambda customer_id: membership,
    )

    monkeypatch.setattr(
        app_module,
        "persist_api_decision",
        lambda customer, membership, decision:
            "DEC-MEMBER-001",
    )

    response = client.get(
        "/nba/C00001"
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["next_best_action"]
        == "INVESTMENT_INFO"
    )

    assert body["score"] == 0.93

    assert (
        "MEMBERSHIP_RECENT_ENGAGEMENT"
        in body["reason_codes"]
    )

    assert (
        "MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION"
        in body["reason_codes"]
    )

    assert (
        response.headers[
            "x-decision-id"
        ]
        == "DEC-MEMBER-001"
    )

    assert "decision_id" not in body


def test_malformed_customer_id_creates_no_audit(
    monkeypatch,
):
    audit_calls = []

    monkeypatch.setattr(
        app_module,
        "persist_api_decision",
        lambda *args: audit_calls.append(
            args
        ),
    )

    response = client.get(
        "/nba/not-a-customer"
    )

    assert response.status_code == 422

    assert audit_calls == []

    assert (
        "x-decision-id"
        not in response.headers
    )


def test_audit_persistence_failure_is_fail_closed(
    monkeypatch,
):
    customer = make_customer()

    monkeypatch.setattr(
        app_module,
        "get_customer",
        lambda customer_id: customer,
    )

    monkeypatch.setattr(
        app_module,
        "get_membership_context",
        lambda customer_id: None,
    )

    def fail_audit(
        customer,
        membership,
        decision,
    ):
        raise RuntimeError(
            "Synthetic audit failure"
        )

    monkeypatch.setattr(
        app_module,
        "persist_api_decision",
        fail_audit,
    )

    response = client.get(
        "/nba/C00001"
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