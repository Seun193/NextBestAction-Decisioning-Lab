from src.batch_reconcile_db_api import compare_response


def valid_expected():
    return {
        "customer_id": "C00001",
        "next_best_action": "SAVINGS_PLAN",
        "score": 0.52,
        "eligible": True,
        "reason_codes": [
            "LOW_SAVINGS_RELATIVE_TO_INCOME",
        ],
        "ranked_actions": [
            {
                "action": "SAVINGS_PLAN",
                "score": 0.52,
                "eligible": True,
                "reason_codes": [
                    "LOW_SAVINGS_RELATIVE_TO_INCOME",
                ],
            }
        ],
    }


def test_matching_response_has_no_mismatches():
    expected = valid_expected()

    actual = {
        "customer_id": "C00001",
        "next_best_action": "SAVINGS_PLAN",
        "score": 0.52,
        "eligible": True,
        "reason_codes": [
            "LOW_SAVINGS_RELATIVE_TO_INCOME",
        ],
        "ranked_actions": [
            {
                "action": "SAVINGS_PLAN",
                "score": 0.52,
                "eligible": True,
                "reason_codes": [
                    "LOW_SAVINGS_RELATIVE_TO_INCOME",
                ],
            }
        ],
    }

    mismatches = compare_response(
        expected,
        200,
        actual,
    )

    assert mismatches == []


def test_wrong_action_is_reported():
    expected = valid_expected()

    actual = expected.copy()
    actual["next_best_action"] = "FINANCIAL_HEALTH_CHECK"

    mismatches = compare_response(
        expected,
        200,
        actual,
    )

    assert any(
        mismatch["field"] == "next_best_action"
        for mismatch in mismatches
    )


def test_wrong_score_is_reported():
    expected = valid_expected()

    actual = expected.copy()
    actual["score"] = 0.99

    mismatches = compare_response(
        expected,
        200,
        actual,
    )

    assert any(
        mismatch["field"] == "score"
        for mismatch in mismatches
    )


def test_http_failure_is_reported():
    expected = valid_expected()

    mismatches = compare_response(
        expected,
        500,
        {},
    )

    assert any(
        mismatch["field"] == "HTTP status"
        for mismatch in mismatches
    )