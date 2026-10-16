import pytest

from crashmodel.engine.bonds import par_bond_returns
from crashmodel.engine.months import Month, MonthlySeries

START = Month(2000, 1)


def one_return(previous: float, current: float, term_years: float = 10) -> float:
    return par_bond_returns(MonthlySeries(START, (previous, current)), term_years)[START + 1]


@pytest.mark.parametrize("yield_percent", [0.5, 4.0, 12.0, -0.2])
def test_an_unchanged_yield_earns_a_month_of_coupon(yield_percent: float) -> None:
    """A negative yield is a coupon paid by the holder, so the month loses it."""
    assert one_return(yield_percent, yield_percent) == pytest.approx(yield_percent / 1200)


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (4.0, 5.0, -0.074109136939),  # duration about 8.1: -8.1% + 0.3% carry + 0.4% convexity
        (5.0, 4.0, 0.085367641035),  # a fall gains more than the same rise loses
        (3.0, 2.0, 0.092047639479),
        (2.0, 3.0, -0.083561633868),
    ],
)
def test_yield_moves_match_hand_worked_values(
    previous: float, current: float, expected: float
) -> None:
    assert one_return(previous, current) == pytest.approx(expected, abs=1e-12)


def test_a_fall_to_a_zero_yield_gains_the_bond_its_whole_annuity() -> None:
    """At a zero yield the annuity factor is n / 200: 0.5/1200 + 0.5 * 2 * (5 - 1/12) / 200."""
    assert one_return(0.5, 0.0, term_years=5) == pytest.approx(0.025)


def test_returns_pass_smoothly_through_a_zero_yield() -> None:
    near = [one_return(0.5, current, term_years=5) for current in (-1e-9, 0.0, 1e-9)]
    assert near == pytest.approx([0.025] * 3)


def test_a_shorter_bond_moves_less_with_the_same_change_in_yield() -> None:
    assert abs(one_return(4.0, 5.0, term_years=5)) < abs(one_return(4.0, 5.0, term_years=10))


def test_returns_start_the_month_after_the_first_yield() -> None:
    returns = par_bond_returns(MonthlySeries(START, (4.0, 4.0, 4.0)), 10)
    assert (returns.start, returns.end) == (START + 1, START + 2)


@pytest.mark.parametrize(
    ("yields", "term_years", "message"),
    [
        ((4.0,), 10, "at least two months"),
        ((4.0, -200.0), 10, "above -200%"),
        ((4.0, 4.0), 1 / 12, "no time left"),
    ],
)
def test_yields_must_span_two_months_and_the_bond_must_outlast_one(
    yields: tuple[float, ...], term_years: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        par_bond_returns(MonthlySeries(START, yields), term_years)
