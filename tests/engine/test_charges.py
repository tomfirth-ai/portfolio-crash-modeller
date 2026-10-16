import pytest
from hypothesis import given
from hypothesis import strategies as st

from crashmodel.engine.charges import after_yearly_charge
from crashmodel.engine.months import Month, MonthlySeries

JANUARY = Month(2020, 1)
ROUNDING = 1e-15


def after(returns: tuple[float, ...], yearly_charge: float) -> tuple[float, ...]:
    return after_yearly_charge(MonthlySeries(JANUARY, returns), yearly_charge).values


@pytest.mark.parametrize(
    ("index_return", "yearly_charge", "fund_return"),
    [
        (0.0, 0.012, -0.001),  # a flat month costs a twelfth of 1.2%
        (0.10, 0.12, 0.089),  # 1.10 * 0.99: the charge is taken on the month's gain too
        (-0.50, 0.12, -0.505),  # 0.50 * 0.99: and on what is left after a fall
        (0.03, 0.0, 0.03),  # an index held directly bears no charge
    ],
)
def test_each_month_keeps_all_but_a_twelfth_of_the_yearly_charge(
    index_return: float, yearly_charge: float, fund_return: float
) -> None:
    assert after((index_return,), yearly_charge) == pytest.approx((fund_return,))


def test_a_year_of_flat_months_costs_a_little_less_than_the_charge() -> None:
    """Each twelfth is charged on what the months before left: 0.99 to the 12th power."""
    [*monthly] = after((0.0,) * 12, 0.12)
    kept = 1.0
    for fund_return in monthly:
        kept *= 1 + fund_return
    assert kept == pytest.approx(0.99**12)
    assert 1 - kept < 0.12


def test_the_months_are_unchanged() -> None:
    charged = after_yearly_charge(MonthlySeries(JANUARY, (0.01, 0.02, 0.03)), 0.0006)
    assert (charged.start, charged.end) == (JANUARY, Month(2020, 3))


@pytest.mark.parametrize("yearly_charge", [-0.001, 1.0, 1.5])
def test_a_charge_outside_zero_to_one_is_refused(yearly_charge: float) -> None:
    with pytest.raises(ValueError, match="not between 0 and 1"):
        after((0.01,), yearly_charge)


@given(
    index_return=st.floats(min_value=-0.99, max_value=1.0),
    yearly_charge=st.floats(min_value=0.0, max_value=0.05),
)
def test_a_charge_never_makes_a_fund_do_better_than_its_index(
    index_return: float, yearly_charge: float
) -> None:
    [fund_return] = after((index_return,), yearly_charge)
    # (1 + r) - 1 rounds a tiny return to zero, so allow for rounding.
    assert fund_return <= index_return + ROUNDING
