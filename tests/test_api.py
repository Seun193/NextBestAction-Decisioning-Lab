from fastapi.testclient import TestClient

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


def test_unknown_customer_returns_404():
    response = client.get(
        "/nba/C99999"
    )

    assert response.status_code == 404


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