from .decision_engine import (
    clamp,
    decide,
)
from .models import (
    ActionScore,
    Customer,
    MembershipContext,
    NBAResponse,
)


DIGITAL_MARKETING_ACTIONS = {
    "SAVINGS_PLAN",
    "INVESTMENT_INFO",
    "CREDIT_CARD_UPGRADE",
}


def apply_membership_relevance(
    action: ActionScore,
    membership: MembershipContext | None,
) -> ActionScore:
    """
    Apply small membership-derived relevance adjustments.

    Membership context may refine ranking only.

    It must never:
    - make an ineligible action eligible
    - override marketing consent
    - override investment consent
    - override affordability or product rules

    Only ACTIVE membership contributes to the current
    relevance adjustment.

    Membership tier, tenure and benefit utilisation are
    intentionally not used as proxies for financial
    suitability.
    """

    if membership is None:
        return action

    if membership.membership_status != "ACTIVE":
        return action

    if not action.eligible:
        return action

    if action.action not in DIGITAL_MARKETING_ACTIONS:
        return action

    score = action.score
    reasons = list(
        action.reason_codes
    )

    if (
        membership.engagement_events_30d
        >= 5
    ):
        score += 0.03

        reasons.append(
            "MEMBERSHIP_RECENT_ENGAGEMENT"
        )

    if (
        membership.campaign_conversions_30d
        >= 1
    ):
        score += 0.04

        reasons.append(
            "MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION"
        )

    elif (
        membership.latest_campaign_response
        == "CLICKED"
    ):
        score += 0.02

        reasons.append(
            "MEMBERSHIP_RECENT_CAMPAIGN_CLICK"
        )

    elif (
        membership.latest_campaign_response
        == "OPENED"
    ):
        score += 0.01

        reasons.append(
            "MEMBERSHIP_RECENT_CAMPAIGN_OPEN"
        )

    return ActionScore(
        action=action.action,
        score=clamp(
            score
        ),
        eligible=action.eligible,
        reason_codes=reasons,
    )


def decide_with_membership(
    customer: Customer,
    membership: MembershipContext | None,
) -> NBAResponse:
    """
    Run the existing NBA decision engine and then apply
    membership-derived relevance adjustments.

    Core product eligibility remains controlled by the
    original decision engine.
    """

    base_result = decide(
        customer
    )

    if membership is None:
        return base_result

    adjusted_actions = [
        apply_membership_relevance(
            action,
            membership,
        )
        for action
        in base_result.ranked_actions
    ]

    ranked = sorted(
        adjusted_actions,
        key=lambda action: (
            action.eligible,
            action.score,
        ),
        reverse=True,
    )

    winner = ranked[0]

    return NBAResponse(
        customer_id=customer.customer_id,
        next_best_action=winner.action,
        score=winner.score,
        eligible=winner.eligible,
        reason_codes=winner.reason_codes,
        ranked_actions=ranked,
    )