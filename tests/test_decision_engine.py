from src.decision_engine import decide
from src.models import Customer


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
    data.update(overrides)
    return Customer(**data)


def test_returns_ranked_actions():
    result = decide(base_customer())
    assert len(result.ranked_actions) == 5
    scores = [a.score for a in result.ranked_actions]
    assert scores == sorted(scores, reverse=True)


def test_investment_is_blocked_without_consent():
    result = decide(base_customer(investment_consent=False))
    investment = next(
        a for a in result.ranked_actions if a.action == "INVESTMENT_INFO"
    )
    assert investment.eligible is False
    assert investment.score == 0
    assert "NO_INVESTMENT_CONSENT" in investment.reason_codes


def test_mortgage_blocked_if_customer_already_has_one():
    result = decide(base_customer(has_mortgage=True))
    mortgage = next(
        a for a in result.ranked_actions if a.action == "MORTGAGE_CONSULTATION"
    )
    assert mortgage.eligible is False
    assert mortgage.score == 0
    assert "ALREADY_HAS_MORTGAGE" in mortgage.reason_codes


def test_financial_health_check_remains_available_without_marketing_consent():
    result = decide(
        base_customer(
            marketing_consent=False,
            monthly_surplus=-400,
            savings_balance=500,
            credit_score_band="LOW",
        )
    )
    assert result.next_best_action == "FINANCIAL_HEALTH_CHECK"
    assert result.eligible is True


def test_winner_is_eligible():
    result = decide(base_customer())
    assert result.eligible is True
