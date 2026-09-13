from src.decision_engine import decide
from src.models import Customer


def base_customer(**overrides):
    data = dict(
        customer_id="BR_TEST",
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

    data.update(overrides)
    return Customer(**data)


def get_action(result, action_name):
    return next(
        action
        for action in result.ranked_actions
        if action.action == action_name
    )


def test_br_sav_001_savings_requires_marketing_consent():
    result = decide(base_customer(marketing_consent=False))
    action = get_action(result, "SAVINGS_PLAN")

    assert action.eligible is False
    assert action.score == 0
    assert "NO_MARKETING_CONSENT" in action.reason_codes


def test_br_inv_001_investment_requires_investment_consent():
    result = decide(base_customer(investment_consent=False))
    action = get_action(result, "INVESTMENT_INFO")

    assert action.eligible is False
    assert action.score == 0
    assert "NO_INVESTMENT_CONSENT" in action.reason_codes


def test_br_mort_001_existing_mortgage_blocks_consultation():
    result = decide(base_customer(has_mortgage=True))
    action = get_action(result, "MORTGAGE_CONSULTATION")

    assert action.eligible is False
    assert action.score == 0
    assert "ALREADY_HAS_MORTGAGE" in action.reason_codes


def test_br_mort_001_customer_under_23_is_ineligible():
    result = decide(base_customer(age=22))
    action = get_action(result, "MORTGAGE_CONSULTATION")

    assert action.eligible is False
    assert action.score == 0


def test_br_cc_001_requires_existing_credit_card():
    result = decide(base_customer(has_credit_card=False))
    action = get_action(result, "CREDIT_CARD_UPGRADE")

    assert action.eligible is False
    assert action.score == 0
    assert "NO_EXISTING_CREDIT_CARD" in action.reason_codes


def test_br_cc_001_low_credit_score_blocks_upgrade():
    result = decide(base_customer(credit_score_band="LOW"))
    action = get_action(result, "CREDIT_CARD_UPGRADE")

    assert action.eligible is False
    assert action.score == 0
    assert "LOW_CREDIT_SCORE_BAND" in action.reason_codes


def test_br_fhc_001_financial_health_check_is_always_eligible():
    result = decide(
        base_customer(
            marketing_consent=False,
            investment_consent=False,
            credit_score_band="LOW",
        )
    )

    action = get_action(result, "FINANCIAL_HEALTH_CHECK")

    assert action.eligible is True


def test_br_rank_001_eligible_actions_rank_before_ineligible_actions():
    result = decide(base_customer())

    eligibility = [
        action.eligible
        for action in result.ranked_actions
    ]

    first_false = (
        eligibility.index(False)
        if False in eligibility
        else len(eligibility)
    )

    assert all(eligibility[:first_false])
    assert not any(eligibility[first_false:])


def test_br_rank_002_scores_descend_within_eligible_actions():
    result = decide(base_customer())

    eligible_scores = [
        action.score
        for action in result.ranked_actions
        if action.eligible
    ]

    assert eligible_scores == sorted(
        eligible_scores,
        reverse=True,
    )


def test_br_win_001_winner_is_top_ranked_eligible_action():
    result = decide(base_customer())

    expected_winner = next(
        action
        for action in result.ranked_actions
        if action.eligible
    )

    assert result.next_best_action == expected_winner.action
    assert result.score == expected_winner.score
    assert result.eligible is True