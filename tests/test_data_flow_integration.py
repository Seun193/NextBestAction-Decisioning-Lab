from src.decision_engine import decide
from src.downstream_adapter import map_nba_to_downstream
from src.upstream_adapter import (
    UpstreamCustomerRecord,
    map_upstream_customer,
)


def test_upstream_to_decisioning_to_downstream_flow():
    upstream = UpstreamCustomerRecord(
        party_id="C90001",
        age_years=35,
        income_monthly_eur=4200.00,
        savings_eur=18000.00,
        surplus_monthly_eur=850.00,
        mortgage_flag="N",
        credit_card_flag="Y",
        investment_customer_flag="N",
        app_visits_30d=12,
        marketing_permission="Y",
        investment_permission="Y",
        credit_score_band="HIGH",
        preferred_contact_channel="MOBILE",
    )

    customer = map_upstream_customer(upstream)

    decision = decide(customer)

    downstream = map_nba_to_downstream(decision)

    assert downstream.party_id == upstream.party_id
    assert downstream.selected_action_code == decision.next_best_action
    assert downstream.selected_score == decision.score
    assert downstream.selected_eligible == decision.eligible
    assert downstream.selected_reason_codes == decision.reason_codes

    assert len(downstream.action_ranking) == len(decision.ranked_actions)

    assert [
        item.action_code for item in downstream.action_ranking
    ] == [
        item.action for item in decision.ranked_actions
    ]