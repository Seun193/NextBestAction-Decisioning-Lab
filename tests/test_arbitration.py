import pytest
from pydantic import ValidationError

from src.arbitration import (
    ArbitrationCandidate,
    arbitrate,
    calculate_arbitration_score,
)


def candidate(
    action: str,
    propensity: float = 0.5,
    context_weight: float = 1.0,
    business_value: float = 1.0,
    business_lever: float = 1.0,
    eligible: bool = True,
    constraint_passed: bool = True,
    priority: int = 1,
    reason_codes=None,
) -> ArbitrationCandidate:
    return ArbitrationCandidate(
        action=action,
        propensity=propensity,
        context_weight=context_weight,
        business_value=business_value,
        business_lever=business_lever,
        eligible=eligible,
        constraint_passed=constraint_passed,
        priority=priority,
        reason_codes=reason_codes or [],
    )


def test_arb_007_arbitration_score_formula():
    item = candidate(
        action="INVESTMENT_INFO",
        propensity=0.8,
        context_weight=1.2,
        business_value=2.0,
        business_lever=1.5,
    )

    score = calculate_arbitration_score(item)

    assert score == pytest.approx(2.88)


def test_arb_008_highest_selectable_score_wins():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.60,
            business_value=1.0,
        ),
        candidate(
            action="INVESTMENT_INFO",
            propensity=0.80,
            business_value=1.0,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "INVESTMENT_INFO"
    assert result.winning_score == pytest.approx(0.80)


def test_arb_001_ineligible_action_cannot_win_even_with_huge_score():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.50,
            business_value=1.0,
            eligible=True,
        ),
        candidate(
            action="INVESTMENT_INFO",
            propensity=1.0,
            context_weight=10.0,
            business_value=10.0,
            business_lever=10.0,
            eligible=False,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "SAVINGS_PLAN"


def test_arb_002_constraint_blocked_action_cannot_win():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.50,
        ),
        candidate(
            action="CREDIT_CARD_UPGRADE",
            propensity=1.0,
            context_weight=10.0,
            business_value=10.0,
            business_lever=10.0,
            constraint_passed=False,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "SAVINGS_PLAN"


def test_arb_009_priority_breaks_equal_score_tie():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.8,
            priority=2,
        ),
        candidate(
            action="INVESTMENT_INFO",
            propensity=0.8,
            priority=1,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "INVESTMENT_INFO"


def test_arb_009_action_code_breaks_complete_tie_deterministically():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.8,
            priority=1,
        ),
        candidate(
            action="INVESTMENT_INFO",
            propensity=0.8,
            priority=1,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "INVESTMENT_INFO"


def test_arb_010_no_selectable_candidate_returns_no_winner():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            eligible=False,
        ),
        candidate(
            action="INVESTMENT_INFO",
            constraint_passed=False,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner is None
    assert result.winning_score is None


def test_arb_011_ranking_exposes_decision_inputs():
    candidates = [
        candidate(
            action="INVESTMENT_INFO",
            propensity=0.75,
            context_weight=1.2,
            business_value=2.0,
            business_lever=1.1,
            priority=3,
            reason_codes=["INVESTMENT_CONSENT"],
        ),
    ]

    result = arbitrate(candidates)

    ranked = result.ranked_candidates[0]

    assert ranked.action == "INVESTMENT_INFO"
    assert ranked.propensity == 0.75
    assert ranked.context_weight == 1.2
    assert ranked.business_value == 2.0
    assert ranked.business_lever == 1.1
    assert ranked.priority == 3
    assert ranked.eligible is True
    assert ranked.constraint_passed is True
    assert ranked.reason_codes == ["INVESTMENT_CONSENT"]


@pytest.mark.parametrize(
    "invalid_propensity",
    [-0.01, 1.01],
)
def test_arb_003_invalid_propensity_is_rejected(invalid_propensity):
    with pytest.raises(ValidationError):
        candidate(
            action="INVESTMENT_INFO",
            propensity=invalid_propensity,
        )


def test_business_lever_can_change_relative_priority():
    candidates = [
        candidate(
            action="SAVINGS_PLAN",
            propensity=0.80,
            business_lever=1.0,
        ),
        candidate(
            action="INVESTMENT_INFO",
            propensity=0.60,
            business_lever=1.5,
        ),
    ]

    result = arbitrate(candidates)

    assert result.winner == "INVESTMENT_INFO"