import math

import pytest

from crashmodel.engine.curves import ZeroCurve
from crashmodel.engine.ladders import Rung, ladder_returns
from crashmodel.engine.months import Month

START = Month(2000, 1)


def flat(yield_percent: float) -> ZeroCurve:
    return ZeroCurve.from_points({0: yield_percent})


def last_return(
    curves: list[ZeroCurve], rungs: list[Rung], issue_terms: tuple[float, ...]
) -> float:
    returns = ladder_returns(curves, START, rungs, issue_terms)
    return returns[returns.end]


def test_on_an_unchanged_flat_curve_every_gilt_grows_at_the_yield() -> None:
    """No coupon falls due within the month, so each gilt's value grows by exp(6 / 1200)."""
    rungs = [Rung(0.5, 1), Rung(7, 2), Rung(40, 1)]
    returns = ladder_returns([flat(6.0)] * 4, START, rungs, (5, 10, 30, 50))
    assert returns.start == START + 1
    assert returns.values == pytest.approx((math.exp(0.005) - 1,) * 3)


def test_a_new_gilt_is_worth_its_face_value_and_is_revalued_a_month_later() -> None:
    """A one-year gilt issued at 4%: coupon 200 * (e^0.02 - 1), then valued at 5% with 5 and 11
    months to its two payments."""
    coupon = 2 * (math.exp(0.02) - 1)
    later = coupon / 2 * math.exp(-0.05 * 5 / 12) + (1 + coupon / 2) * math.exp(-0.05 * 11 / 12)
    assert last_return([flat(4.0), flat(5.0)], [Rung(1, 1)], (1,)) == pytest.approx(later - 1)


def test_a_gilt_keeps_the_coupon_it_was_issued_with() -> None:
    """Issued at 8%, six months before yields stood at 2%, it falls less on a rise to 3% than a
    gilt issued at 2%: more of its value comes back sooner."""
    issued_high = [flat(8.0)] + [flat(2.0)] * 6 + [flat(3.0)]
    issued_low = [flat(2.0)] * 7 + [flat(3.0)]
    high, low = (last_return(curves, [Rung(1, 1)], (1.5,)) for curves in (issued_high, issued_low))
    assert low < high < 0


def test_a_gilt_issued_before_the_first_curve_takes_that_curves_coupon() -> None:
    """A five-year gilt with one year left was issued 48 months before the first curve."""
    short_history = [flat(6.0), flat(3.0)]
    long_history = [flat(6.0)] * 49 + [flat(3.0)]
    rung = [Rung(1, 1)]
    assert last_return(short_history, rung, (5,)) == pytest.approx(
        last_return(long_history, rung, (5,))
    )


def test_longer_rungs_lose_more_when_yields_rise() -> None:
    curves = [flat(3.0), flat(4.0)]
    short, long = (last_return(curves, [Rung(years, 1)], (30,)) for years in (2, 20))
    assert long < short < 0


def test_a_rungs_face_value_is_split_between_the_terms_issued_for_at_least_its_time_left() -> None:
    """The one-year rung holds gilts first issued at 1.5 and 5 years, half its face value each;
    the two-year rung only 5-year gilts. All are zero-coupon, worth 1/2 and 1/4 of face, then face:
    split, the ladder goes from 3/4 to 2, a return of 5/3; counted once per term, the one-year
    rung would hold twice its face value, and the return would be 3 / (5/4) - 1 = 7/5."""
    curves = [flat(0.0), flat(100 * math.log(2)), flat(0.0)]
    assert last_return(curves, [Rung(1, 1), Rung(2, 1)], (1.5, 5)) == pytest.approx(5 / 3)


def test_each_gilt_in_a_rung_holds_an_equal_share_and_keeps_its_own_coupon() -> None:
    """The one-year rung holds, half each, a one-year gilt bought new on a curve with D(0.5) = 1
    and D(1) = 0.8 (coupon 1/9 a half year, worth 1, then 11/9 on a curve at 0) and a gilt first
    issued at 1.5 years, six months before, at exactly 4% (worth 0.02 * 1.8 + 0.8 = 0.836, then
    1.04). Held only in the first, the return would be 2/9."""
    sloped = ZeroCurve.from_points({0.5: 0.0, 1: 100 * math.log(1.25)})
    curves = [flat(200 * math.log(1.02))] + [flat(0.0)] * 5 + [sloped, flat(0.0)]
    expected = (11 / 18 + 0.52) / (1 / 2 + 0.418) - 1
    assert last_return(curves, [Rung(1, 1)], (1, 1.5)) == pytest.approx(expected)


def test_a_gilt_takes_the_par_coupon_of_its_own_issue_term() -> None:
    """Issued at one year on a curve with D(0.5) = 1 and D(1) = 0.8, its coupon is 1/9 a half
    year: (1/9) * 1.8 + 0.8 = 1. On a curve at 0 a month later it is worth 2/9 + 1, a return of
    2/9; with the half-year term's coupon, 0, it would be 1 / 0.8 - 1 = 1/4."""
    sloped = ZeroCurve.from_points({0.5: 0.0, 1: 100 * math.log(1.25)})
    assert last_return([sloped, flat(0.0)], [Rung(1, 1)], (1,)) == pytest.approx(2 / 9)


@pytest.mark.parametrize(
    ("curves", "rungs", "issue_terms", "message"),
    [
        ([flat(3.0)], [Rung(1, 1)], (5,), "at least two months"),
        ([flat(3.0)] * 2, [], (5,), "at least one rung"),
        ([flat(3.0)] * 2, [Rung(10, 1)], (5,), "long enough"),
    ],
)
def test_a_ladder_needs_two_curves_and_rungs_its_gilts_can_reach(
    curves: list[ZeroCurve], rungs: list[Rung], issue_terms: tuple[float, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ladder_returns(curves, START, rungs, issue_terms)


@pytest.mark.parametrize(
    ("years_left", "weight", "message"),
    [(0, 1, "half years"), (0.3, 1, "half years"), (1, 0, "some of the gilts")],
)
def test_a_rung_is_whole_half_years_and_holds_money(
    years_left: float, weight: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Rung(years_left, weight)


def test_with_no_interest_anywhere_every_gilt_returns_nothing() -> None:
    returns = ladder_returns([flat(0.0)] * 3, START, [Rung(0.5, 1), Rung(30, 1)], (5, 50))
    assert returns.values == (0.0, 0.0)


@pytest.mark.parametrize(("years_left", "exponent"), [(0.5, 0.005), (1, 0.011), (5, 0.059)])
def test_a_zero_coupon_gilt_falls_with_the_yield_on_its_remaining_term(
    years_left: float, exponent: float
) -> None:
    """Issued when rates were 0, its coupon is 0; at 1.2% a pound due in s - 1/12 years is worth
    exp(-0.012 * (s - 1/12))."""
    curves = [flat(0.0), flat(0.0), flat(1.2)]
    assert last_return(curves, [Rung(years_left, 1)], (5,)) == pytest.approx(
        math.exp(-exponent) - 1
    )


def test_a_gilt_takes_the_coupon_of_the_month_it_was_issued_exactly() -> None:
    """A curve flat at 200 * ln(1.02) gives a coupon of exactly 4%. This gilt, a year and a half
    long, was issued six months before the month its year-left rung is bought, at that curve."""
    at_four = flat(200 * math.log(1.02))
    curves = [at_four] + [flat(2.0)] * 6 + [flat(3.0)]
    worth_before = 0.02 * (math.exp(-0.01) + math.exp(-0.02)) + math.exp(-0.02)
    worth_after = 0.02 * (math.exp(-0.03 * 5 / 12) + math.exp(-0.03 * 11 / 12)) + math.exp(
        -0.03 * 11 / 12
    )
    expected = worth_after / worth_before - 1
    assert last_return(curves, [Rung(1, 1)], (1.5,)) == pytest.approx(expected)
    month_later = [flat(2.0), at_four] + [flat(2.0)] * 5 + [flat(3.0)]
    assert last_return(month_later, [Rung(1, 1)], (1.5,)) != pytest.approx(expected)


def test_rungs_are_counted_at_face_value_as_an_index_counts_gilts_in_issue() -> None:
    """Zero-coupon gilts worth 1/2 and 1/4 of face value, both then worth face: the ladder's value
    goes from 3/4 to 2, a return of 2 / (3/4) - 1 = 5/3, not the average of the returns, 2."""
    curves = [flat(0.0), flat(100 * math.log(2)), flat(0.0)]
    assert last_return(curves, [Rung(1, 1), Rung(2, 1)], (5,)) == pytest.approx(5 / 3)
