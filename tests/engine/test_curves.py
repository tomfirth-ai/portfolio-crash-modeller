import math

import pytest

from crashmodel.engine.curves import ZeroCurve, continuous_overnight_rate, par_coupon

CURVE = ZeroCurve.from_points({20: 6.0, 0: 2.0, 10: 5.0, 5: 4.0})


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        (0, 2.0),
        (2.5, 3.0),  # halfway from 2% at once to 4% at 5 years
        (5, 4.0),
        (7.5, 4.5),
        (15, 5.5),
        (20, 6.0),
        (50, 6.0),  # flat beyond the last point
    ],
)
def test_yields_lie_on_straight_lines_between_points_and_flat_beyond(
    term: float, expected: float
) -> None:
    assert CURVE.yield_at(term) == pytest.approx(expected)


def test_a_curve_starting_after_zero_is_flat_before_its_first_point() -> None:
    assert ZeroCurve.from_points({5: 4.0, 10: 5.0}).yield_at(1) == 4.0


def test_a_pound_due_later_is_worth_less_at_the_yield_for_its_term() -> None:
    assert CURVE.discount(10) == pytest.approx(math.exp(-0.5))
    assert CURVE.discount(0) == 1.0


def test_on_a_flat_curve_the_par_coupon_matches_the_yield_compounded_half_yearly() -> None:
    """With D(k/2) = q ** k and q = exp(-z/200), the coupon is 200 * (1/q - 1) whatever the term."""
    flat = ZeroCurve.from_points({0: 4.0})
    expected = 200 * (math.exp(0.02) - 1)
    assert [par_coupon(flat, term) for term in (0.5, 5, 50)] == pytest.approx([expected] * 3)


def test_on_a_negative_curve_the_par_coupon_is_negative() -> None:
    """Holders pay to own gilts at negative yields: 200 * (exp(-0.005) - 1) a year at -1%."""
    assert par_coupon(ZeroCurve.from_points({0: -1.0}), 5) == pytest.approx(
        200 * (math.exp(-0.005) - 1)
    )


def test_a_curve_known_to_10_years_stays_at_its_10_year_yield_beyond() -> None:
    curve = ZeroCurve.from_points({0: 1.0, 5: 3.0, 10: 4.0})
    assert [curve.yield_at(term) for term in (12, 50)] == [4.0, 4.0]


def test_a_par_coupon_prices_its_gilt_at_face_value() -> None:
    coupon = par_coupon(CURVE, 10)
    discounts = [CURVE.discount(k / 2) for k in range(1, 21)]
    assert coupon / 200 * sum(discounts) + discounts[-1] == pytest.approx(1.0)


def test_an_overnight_rate_is_worth_a_little_less_continuously_compounded() -> None:
    """Earning 3.65 / 365 = 0.01% a day: 365 * ln(1.0001) a year continuously compounded."""
    assert continuous_overnight_rate(3.65) == pytest.approx(36500 * math.log(1.0001))
    assert continuous_overnight_rate(3.65) < 3.65


@pytest.mark.parametrize(
    ("points", "message"), [({}, "at least one point"), ({-1: 2.0}, "zero or more")]
)
def test_a_curve_needs_points_at_terms_of_zero_or_more(
    points: dict[float, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ZeroCurve.from_points(points)


def test_terms_must_increase() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        ZeroCurve(((5, 4.0), (5, 4.5)))


@pytest.mark.parametrize("term", [0, -1, 0.3])
def test_a_gilt_runs_for_a_whole_number_of_half_years(term: float) -> None:
    with pytest.raises(ValueError, match="half years"):
        par_coupon(CURVE, term)
