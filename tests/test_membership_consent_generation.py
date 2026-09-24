import pytest

from src.generate_membership_data import (
    membership_consent,
    parse_boolean_style,
)


class FixedRandom:
    def __init__(
        self,
        value: float,
    ):
        self.value = value

    def random(self) -> float:
        return self.value


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("True", 1),
        ("true", 1),
        ("1", 1),
        (True, 1),
        (1, 1),
        ("False", 0),
        ("false", 0),
        ("0", 0),
        (False, 0),
        (0, 0),
    ],
)
def test_parse_boolean_style(
    raw_value,
    expected,
):
    assert (
        parse_boolean_style(
            raw_value,
            "marketing_consent",
        )
        == expected
    )


def test_invalid_boolean_style_is_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "marketing_consent must be "
            "0/1/true/false"
        ),
    ):
        parse_boolean_style(
            "YES",
            "marketing_consent",
        )


def test_false_string_remains_false_without_mismatch():
    rng = FixedRandom(
        0.50,
    )

    assert (
        membership_consent(
            "False",
            rng,
        )
        == 0
    )


def test_true_string_remains_true_without_mismatch():
    rng = FixedRandom(
        0.50,
    )

    assert (
        membership_consent(
            "True",
            rng,
        )
        == 1
    )


def test_false_string_can_be_deliberately_mismatched():
    rng = FixedRandom(
        0.001,
    )

    assert (
        membership_consent(
            "False",
            rng,
        )
        == 1
    )


def test_true_string_can_be_deliberately_mismatched():
    rng = FixedRandom(
        0.001,
    )

    assert (
        membership_consent(
            "True",
            rng,
        )
        == 0
    )