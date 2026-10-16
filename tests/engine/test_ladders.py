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


def test_a_rungs_money_is_split_between_the_terms_long_enough_to_reach_it() -> None:
    """Equal weights on two identical rungs give the same return as either one alone."""
    curves = [flat(3.0), flat(4.0)]
    alone = last_return(curves, [Rung(3, 1)], (5, 10))
    assert last_return(curves, [Rung(3, 1), Rung(3, 2)], (5, 10)) == pytest.approx(alone)


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
    [(0, 1, "half years"), (0.3, 1, "half years"), (1, 0, "some of the money")],
)
def test_a_rung_is_whole_half_years_and_holds_money(
    years_left: float, weight: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Rung(years_left, weight)
