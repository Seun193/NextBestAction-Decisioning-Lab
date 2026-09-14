from typing import List, Optional

from pydantic import BaseModel, Field


class ArbitrationCandidate(BaseModel):
    action: str
    propensity: float = Field(ge=0.0, le=1.0)
    context_weight: float = Field(ge=0.0)
    business_value: float = Field(ge=0.0)
    business_lever: float = Field(ge=0.0)

    eligible: bool
    constraint_passed: bool

    priority: int = Field(ge=1)
    reason_codes: List[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    action: str
    arbitration_score: float
    eligible: bool
    constraint_passed: bool
    propensity: float
    context_weight: float
    business_value: float
    business_lever: float
    priority: int
    reason_codes: List[str]


class ArbitrationResult(BaseModel):
    winner: Optional[str]
    winning_score: Optional[float]
    ranked_candidates: List[RankedCandidate]


def calculate_arbitration_score(
    candidate: ArbitrationCandidate,
) -> float:
    return (
        candidate.propensity
        * candidate.context_weight
        * candidate.business_value
        * candidate.business_lever
    )


def arbitrate(
    candidates: List[ArbitrationCandidate],
) -> ArbitrationResult:
    ranked = [
        RankedCandidate(
            action=candidate.action,
            arbitration_score=calculate_arbitration_score(candidate),
            eligible=candidate.eligible,
            constraint_passed=candidate.constraint_passed,
            propensity=candidate.propensity,
            context_weight=candidate.context_weight,
            business_value=candidate.business_value,
            business_lever=candidate.business_lever,
            priority=candidate.priority,
            reason_codes=list(candidate.reason_codes),
        )
        for candidate in candidates
    ]

    ranked.sort(
        key=lambda candidate: (
            not (
                candidate.eligible
                and candidate.constraint_passed
            ),
            -candidate.arbitration_score,
            candidate.priority,
            candidate.action,
        )
    )

    selectable = [
        candidate
        for candidate in ranked
        if candidate.eligible
        and candidate.constraint_passed
    ]

    if not selectable:
        return ArbitrationResult(
            winner=None,
            winning_score=None,
            ranked_candidates=ranked,
        )

    winner = selectable[0]

    return ArbitrationResult(
        winner=winner.action,
        winning_score=winner.arbitration_score,
        ranked_candidates=ranked,
    )