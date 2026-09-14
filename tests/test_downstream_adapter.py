from src.downstream_adapter import map_nba_to_downstream
from src.models import ActionScore, NBAResponse


def sample_nba_response() -> NBAResponse:
    return NBAResponse(
        customer_id="C00001",
        next_best_action="INVESTMENT_INFO",
        score=0.82,
        eligible=True,
        reason_codes=[
            "INVESTMENT_CONSENT",
            "HIGH_SAVINGS_BALANCE",
        ],
        ranked_actions=[
            ActionScore(
                action="INVESTMENT_INFO",
                score=0.82,
                eligible=True,
                reason_codes=[
                    "INVESTMENT_CONSENT",
                    "HIGH_SAVINGS_BALANCE",
                ],
            ),
            ActionScore(
                action="SAVINGS_PLAN",
                score=0.61,
                eligible=True,
                reason_codes=[
                    "POSITIVE_MONTHLY_SURPLUS",
                ],
            ),
            ActionScore(
                action="MORTGAGE_CONSULTATION",
                score=0.40,
                eligible=False,
                reason_codes=[
                    "EXISTING_MORTGAGE",
                ],
            ),
        ],
    )


def test_downstream_selected_action_fields_are_preserved():
    response = sample_nba_response()

    record = map_nba_to_downstream(response)

    assert record.party_id == "C00001"
    assert record.selected_action_code == "INVESTMENT_INFO"
    assert record.selected_score == 0.82
    assert record.selected_eligible is True


def test_downstream_selected_reason_codes_are_preserved():
    response = sample_nba_response()

    record = map_nba_to_downstream(response)

    assert record.selected_reason_codes == [
        "INVESTMENT_CONSENT",
        "HIGH_SAVINGS_BALANCE",
    ]


def test_downstream_ranked_action_order_is_preserved():
    response = sample_nba_response()

    record = map_nba_to_downstream(response)

    assert [item.action_code for item in record.action_ranking] == [
        "INVESTMENT_INFO",
        "SAVINGS_PLAN",
        "MORTGAGE_CONSULTATION",
    ]


def test_downstream_ranked_action_values_are_preserved():
    response = sample_nba_response()

    record = map_nba_to_downstream(response)

    first = record.action_ranking[0]
    second = record.action_ranking[1]
    third = record.action_ranking[2]

    assert first.decision_score == 0.82
    assert first.is_eligible is True

    assert second.decision_score == 0.61
    assert second.is_eligible is True

    assert third.decision_score == 0.40
    assert third.is_eligible is False
    assert third.decision_reasons == ["EXISTING_MORTGAGE"]