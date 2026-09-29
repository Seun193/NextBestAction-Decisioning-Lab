from datetime import date, datetime, timedelta

import pytest

from src.generate_campaign_interactions import (
    MAX_RESPONSE_DAYS,
    parse_consent,
    response_timestamp,
)


class UpperBoundRandom:
    """
    Deterministic test double that always chooses
    the maximum allowed randint value.
    """

    def randint(
        self,
        lower: int,
        upper: int,
    ) -> int:
        assert lower == 1
        return upper


def test_customer_consent_false_string_is_zero():
    assert (
        parse_consent(
            "False",
            "customer_marketing_consent",
        )
        == 0
    )


def test_customer_consent_true_string_is_one():
    assert (
        parse_consent(
            "True",
            "customer_marketing_consent",
        )
        == 1
    )


def test_invalid_consent_is_rejected():
    with pytest.raises(
        ValueError,
        match="must be 0/1/true/false",
    ):
        parse_consent(
            "YES",
            "customer_marketing_consent",
        )


def test_ignored_response_has_no_timestamp():
    sent = datetime(
        2026,
        8,
        1,
        8,
        0,
        0,
    )

    result = response_timestamp(
        sent_timestamp=sent,
        response_type="IGNORED",
        as_of_date=date(
            2026,
            9,
            21,
        ),
        rng=UpperBoundRandom(),
    )

    assert result == ""


def test_response_cannot_exceed_exact_seven_day_window():
    sent = datetime(
        2026,
        8,
        1,
        8,
        0,
        0,
    )

    result = datetime.fromisoformat(
        response_timestamp(
            sent_timestamp=sent,
            response_type="OPENED",
            as_of_date=date(
                2026,
                9,
                21,
            ),
            rng=UpperBoundRandom(),
        )
    )

    expected_latest = (
        sent
        + timedelta(
            days=MAX_RESPONSE_DAYS
        )
    )

    assert result == expected_latest


def test_response_window_is_capped_by_as_of_date():
    sent = datetime(
        2026,
        9,
        21,
        20,
        0,
        0,
    )

    result = datetime.fromisoformat(
        response_timestamp(
            sent_timestamp=sent,
            response_type="CLICKED",
            as_of_date=date(
                2026,
                9,
                21,
            ),
            rng=UpperBoundRandom(),
        )
    )

    assert result == datetime(
        2026,
        9,
        21,
        23,
        59,
        59,
    )


@pytest.mark.parametrize(
    "response_type",
    [
        "OPENED",
        "CLICKED",
        "CONVERTED",
    ],
)
def test_actual_response_is_after_send(
    response_type,
):
    sent = datetime(
        2026,
        8,
        1,
        12,
        0,
        0,
    )

    result = datetime.fromisoformat(
        response_timestamp(
            sent_timestamp=sent,
            response_type=response_type,
            as_of_date=date(
                2026,
                9,
                21,
            ),
            rng=UpperBoundRandom(),
        )
    )

    assert result > sent