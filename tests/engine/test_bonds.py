import pytest

from crashmodel.engine.bonds import par_bond_returns
from crashmodel.engine.months import Month, MonthlySeries

START = Month(2000, 1)


def one_return(previous: float, current: float) -> float:
    return par_bond_returns(MonthlySeries(START, (previous, current)))[START + 1]


@pytest.mark.parametrize("yield_percent", [0.5, 4.0, 12.0])
def test_an_unchanged_yield_earns_a_month_of_coupon(yield_percent: float) -> None:
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


def test_returns_start_the_month_after_the_first_yield() -> None:
    returns = par_bond_returns(MonthlySeries(START, (4.0, 4.0, 4.0)))
    assert (returns.start, returns.end) == (START + 1, START + 2)


@pytest.mark.parametrize(
    ("yields", "message"),
    [((4.0,), "at least two months"), ((4.0, 0.0), "positive"), ((-0.1, 4.0), "positive")],
)
def test_yields_must_be_positive_and_span_two_months(
    yields: tuple[float, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        par_bond_returns(MonthlySeries(START, yields))
