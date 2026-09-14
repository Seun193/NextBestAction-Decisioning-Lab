from typing import List

from pydantic import BaseModel

from .models import NBAResponse


class DownstreamRankedAction(BaseModel):
    action_code: str
    decision_score: float
    is_eligible: bool
    decision_reasons: List[str]


class DownstreamDecisionRecord(BaseModel):
    party_id: str
    selected_action_code: str
    selected_score: float
    selected_eligible: bool
    selected_reason_codes: List[str]
    action_ranking: List[DownstreamRankedAction]


def map_nba_to_downstream(response: NBAResponse) -> DownstreamDecisionRecord:
    return DownstreamDecisionRecord(
        party_id=response.customer_id,
        selected_action_code=response.next_best_action,
        selected_score=response.score,
        selected_eligible=response.eligible,
        selected_reason_codes=list(response.reason_codes),
        action_ranking=[
            DownstreamRankedAction(
                action_code=action.action,
                decision_score=action.score,
                is_eligible=action.eligible,
                decision_reasons=list(action.reason_codes),
            )
            for action in response.ranked_actions
        ],
    )