from src.decision_engine import decide
from src.membership_decisioning import (
    decide_with_membership,
)
from src.models import (
    Customer,
    MembershipContext,
)


def base_customer(**overrides):
    data = dict(
        customer_id="TEST001",
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

    data.update(
        overrides
    )

    return Customer(
        **data
    )


def membership_context(
    **overrides,
):
    data = dict(
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

    data.update(
        overrides
    )

    return MembershipContext(
        **data
    )


def action_by_name(
    result,
    name,
):
    return next(
        action
        for action
        in result.ranked_actions
        if action.action == name
    )


def test_no_membership_context_preserves_original_decision():
    customer = base_customer()

    original = decide(
        customer
    )

    integrated = decide_with_membership(
        customer,
        None,
    )

    assert integrated == original


def test_active_membership_engagement_boosts_digital_actions():
    customer = base_customer()

    original = decide(
        customer
    )

    integrated = decide_with_membership(
        customer,
        membership_context(),
    )

    original_investment = action_by_name(
        original,
        "INVESTMENT_INFO",
    )

    integrated_investment = action_by_name(
        integrated,
        "INVESTMENT_INFO",
    )

    assert (
        integrated_investment.score
        == 0.93
    )

    assert (
        integrated_investment.score
        > original_investment.score
    )

    assert (
        "MEMBERSHIP_RECENT_ENGAGEMENT"
        in integrated_investment.reason_codes
    )

    assert (
        "MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION"
        in integrated_investment.reason_codes
    )


def test_membership_context_does_not_change_non_digital_actions():
    customer = base_customer()

    original = decide(
        customer
    )

    integrated = decide_with_membership(
        customer,
        membership_context(),
    )

    original_mortgage = action_by_name(
        original,
        "MORTGAGE_CONSULTATION",
    )

    integrated_mortgage = action_by_name(
        integrated,
        "MORTGAGE_CONSULTATION",
    )

    original_health = action_by_name(
        original,
        "FINANCIAL_HEALTH_CHECK",
    )

    integrated_health = action_by_name(
        integrated,
        "FINANCIAL_HEALTH_CHECK",
    )

    assert (
        integrated_mortgage
        == original_mortgage
    )

    assert (
        integrated_health
        == original_health
    )


def test_membership_context_cannot_override_marketing_consent():
    customer = base_customer(
        marketing_consent=False,
    )

    result = decide_with_membership(
        customer,
        membership_context(),
    )

    for action_name in (
        "SAVINGS_PLAN",
        "INVESTMENT_INFO",
        "MORTGAGE_CONSULTATION",
        "CREDIT_CARD_UPGRADE",
    ):
        action = action_by_name(
            result,
            action_name,
        )

        assert action.eligible is False
        assert action.score == 0

    assert (
        result.next_best_action
        == "FINANCIAL_HEALTH_CHECK"
    )


def test_inactive_membership_does_not_adjust_scores():
    customer = base_customer()

    original = decide(
        customer
    )

    integrated = decide_with_membership(
        customer,
        membership_context(
            membership_status="INACTIVE",
        ),
    )

    assert integrated == original


def test_membership_relevance_can_change_action_ranking():
    customer = base_customer()

    original = decide(
        customer
    )

    integrated = decide_with_membership(
        customer,
        membership_context(),
    )

    assert (
        original.next_best_action
        == "MORTGAGE_CONSULTATION"
    )

    assert (
        integrated.next_best_action
        == "INVESTMENT_INFO"
    )

    assert (
        integrated.score
        == 0.93
    )