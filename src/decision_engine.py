from typing import Callable, Dict, List
from .models import Customer, ActionScore, NBAResponse


ActionFn = Callable[[Customer], ActionScore]


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def savings_plan(c: Customer) -> ActionScore:
    reasons: List[str] = []
    eligible = c.marketing_consent

    score = 0.10

    if c.monthly_surplus > 300:
        score += 0.30
        reasons.append("HAS_MONTHLY_SURPLUS")

    savings_to_income = c.savings_balance / max(c.monthly_income, 1)

    if savings_to_income < 4:
        score += 0.22
        reasons.append("LOW_SAVINGS_RELATIVE_TO_INCOME")

    if c.app_visits_30d >= 8:
        score += 0.12
        reasons.append("DIGITAL_ENGAGEMENT")

    if c.preferred_channel in {"MOBILE", "WEB"}:
        score += 0.08
        reasons.append("DIGITAL_CHANNEL_PREFERENCE")

    if not c.marketing_consent:
        reasons.append("NO_MARKETING_CONSENT")

    return ActionScore(
        action="SAVINGS_PLAN",
        score=clamp(score if eligible else 0),
        eligible=eligible,
        reason_codes=reasons,
    )


def investment_info(c: Customer) -> ActionScore:
    reasons: List[str] = []
    eligible = c.marketing_consent and c.investment_consent and c.age >= 18

    score = 0.08

    if c.savings_balance >= 15000:
        score += 0.30
        reasons.append("SUBSTANTIAL_SAVINGS")

    if c.monthly_income >= 4000:
        score += 0.20
        reasons.append("HIGHER_INCOME")

    if c.monthly_surplus >= 500:
        score += 0.18
        reasons.append("AVAILABLE_MONTHLY_SURPLUS")

    if c.app_visits_30d >= 6:
        score += 0.10
        reasons.append("DIGITAL_ENGAGEMENT")

    if c.investment_customer:
        score += 0.08
        reasons.append("EXISTING_INVESTMENT_RELATIONSHIP")

    if not c.investment_consent:
        reasons.append("NO_INVESTMENT_CONSENT")

    if not c.marketing_consent:
        reasons.append("NO_MARKETING_CONSENT")

    return ActionScore(
        action="INVESTMENT_INFO",
        score=clamp(score if eligible else 0),
        eligible=eligible,
        reason_codes=reasons,
    )


def mortgage_consultation(c: Customer) -> ActionScore:
    reasons: List[str] = []
    eligible = c.marketing_consent and not c.has_mortgage and c.age >= 23

    score = 0.05

    if 25 <= c.age <= 50:
        score += 0.24
        reasons.append("MORTGAGE_RELEVANT_AGE_RANGE")

    if c.monthly_income >= 3200:
        score += 0.25
        reasons.append("INCOME_SUPPORTS_AFFORDABILITY")

    if c.savings_balance >= 10000:
        score += 0.20
        reasons.append("HAS_DOWNPAYMENT_SAVINGS")

    if c.credit_score_band == "HIGH":
        score += 0.14
        reasons.append("HIGH_CREDIT_SCORE_BAND")

    if c.has_mortgage:
        reasons.append("ALREADY_HAS_MORTGAGE")

    if not c.marketing_consent:
        reasons.append("NO_MARKETING_CONSENT")

    return ActionScore(
        action="MORTGAGE_CONSULTATION",
        score=clamp(score if eligible else 0),
        eligible=eligible,
        reason_codes=reasons,
    )


def credit_card_upgrade(c: Customer) -> ActionScore:
    reasons: List[str] = []
    eligible = (
        c.marketing_consent
        and c.has_credit_card
        and c.credit_score_band != "LOW"
    )

    score = 0.06

    if c.monthly_income >= 3500:
        score += 0.28
        reasons.append("INCOME_SUPPORTS_UPGRADE")

    if c.credit_score_band == "HIGH":
        score += 0.25
        reasons.append("HIGH_CREDIT_SCORE_BAND")

    if c.app_visits_30d >= 10:
        score += 0.14
        reasons.append("HIGH_DIGITAL_ENGAGEMENT")

    if not c.has_credit_card:
        reasons.append("NO_EXISTING_CREDIT_CARD")

    if c.credit_score_band == "LOW":
        reasons.append("LOW_CREDIT_SCORE_BAND")

    if not c.marketing_consent:
        reasons.append("NO_MARKETING_CONSENT")

    return ActionScore(
        action="CREDIT_CARD_UPGRADE",
        score=clamp(score if eligible else 0),
        eligible=eligible,
        reason_codes=reasons,
    )


def financial_health_check(c: Customer) -> ActionScore:
    reasons: List[str] = []
    eligible = True

    score = 0.12

    if c.monthly_surplus < 0:
        score += 0.38
        reasons.append("NEGATIVE_MONTHLY_SURPLUS")

    if c.savings_balance < c.monthly_income:
        score += 0.24
        reasons.append("LOW_EMERGENCY_SAVINGS")

    if c.credit_score_band == "LOW":
        score += 0.18
        reasons.append("LOW_CREDIT_SCORE_BAND")

    return ActionScore(
        action="FINANCIAL_HEALTH_CHECK",
        score=clamp(score),
        eligible=eligible,
        reason_codes=reasons,
    )


ACTION_FUNCTIONS: Dict[str, ActionFn] = {
    "SAVINGS_PLAN": savings_plan,
    "INVESTMENT_INFO": investment_info,
    "MORTGAGE_CONSULTATION": mortgage_consultation,
    "CREDIT_CARD_UPGRADE": credit_card_upgrade,
    "FINANCIAL_HEALTH_CHECK": financial_health_check,
}


def decide(customer: Customer) -> NBAResponse:
    results = [fn(customer) for fn in ACTION_FUNCTIONS.values()]

    ranked = sorted(
        results,
        key=lambda x: (x.eligible, x.score),
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
