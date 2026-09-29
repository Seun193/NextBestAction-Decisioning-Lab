from typing import List

from pydantic import BaseModel, Field


class Customer(BaseModel):
    customer_id: str
    age: int = Field(ge=18, le=100)
    monthly_income: float = Field(ge=0)
    savings_balance: float = Field(ge=0)
    monthly_surplus: float
    has_mortgage: bool
    has_credit_card: bool
    investment_customer: bool
    app_visits_30d: int = Field(ge=0)
    marketing_consent: bool
    investment_consent: bool
    credit_score_band: str
    preferred_channel: str


class MembershipContext(BaseModel):
    member_id: str
    membership_status: str
    membership_tier: str

    tenure_days: int = Field(ge=0)
    engagement_events_30d: int = Field(ge=0)
    successful_benefit_redemptions_30d: int = Field(ge=0)
    campaign_sends_30d: int = Field(ge=0)
    campaign_conversions_30d: int = Field(ge=0)

    latest_campaign_response: str | None = None


class ActionScore(BaseModel):
    action: str
    score: float
    eligible: bool
    reason_codes: List[str]


class NBAResponse(BaseModel):
    customer_id: str
    next_best_action: str
    score: float
    eligible: bool
    reason_codes: List[str]
    ranked_actions: List[ActionScore]