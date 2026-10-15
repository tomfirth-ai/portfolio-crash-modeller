from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from crashmodel.engine.currency import month_end_rates, to_home_currency
from crashmodel.engine.months import Month, MonthlySeries

JANUARY = Month(2020, 1)
FEBRUARY = Month(2020, 2)


def convert(foreign_return: float, rate_before: float, rate_after: float) -> float:
    returns = MonthlySeries(FEBRUARY, (foreign_return,))
    rates = MonthlySeries(JANUARY, (rate_before, rate_after))
    return to_home_currency(returns, rates)[FEBRUARY]


@pytest.mark.parametrize(
    ("foreign_return", "rate_before", "rate_after", "home_return"),
    [
        (0.0, 2.00, 1.60, 0.25),  # the pound falls 20%: dollars are worth 25% more in pounds
        (-0.50, 2.00, 1.00, 0.0),  # the sterling cushion: adding the returns would give +50%
        (0.10, 2.00, 2.50, -0.12),  # the pound rises 25%: a 10% gain becomes a 12% loss
        (0.07, 1.50, 1.50, 0.07),  # an unchanged rate passes the return through
    ],
)
def test_returns_are_converted_by_multiplying_not_adding(
    foreign_return: float, rate_before: float, rate_after: float, home_return: float
) -> None:
    assert convert(foreign_return, rate_before, rate_after) == pytest.approx(home_return)


def test_conversion_covers_months_with_a_return_and_both_rates() -> None:
    returns = MonthlySeries(Month(2019, 12), (0.01, 0.02, 0.03, 0.04))
    rates = MonthlySeries(Month(2019, 12), (1.0, 1.0, 1.0))
    converted = to_home_currency(returns, rates)
    assert (converted.start, converted.end) == (JANUARY, FEBRUARY)


def test_conversion_needs_months_in_common() -> None:
    with pytest.raises(ValueError, match="no month in common"):
        to_home_currency(MonthlySeries(JANUARY, (0.01,)), MonthlySeries(JANUARY, (1.0,)))


def test_month_end_rates_take_the_last_day_with_a_rate() -> None:
    rates = month_end_rates(
        [(date(2020, 1, 30), 1.9), (date(2020, 1, 31), 2.0), (date(2020, 2, 28), 2.1)]
    )
    assert rates == MonthlySeries(JANUARY, (2.0, 2.1))


def test_month_end_rates_refuse_days_out_of_order_or_missing_months() -> None:
    with pytest.raises(ValueError, match="date order"):
        month_end_rates([(date(2020, 1, 31), 2.0), (date(2020, 1, 30), 1.9)])
    with pytest.raises(ValueError, match="no gaps"):
        month_end_rates([(date(2020, 1, 31), 2.0), (date(2020, 3, 31), 2.1)])


returns_strategy = st.floats(min_value=-0.9, max_value=2.0)
rates_strategy = st.floats(min_value=0.5, max_value=3.0)


@given(returns_strategy, rates_strategy, rates_strategy)
def test_converting_there_and_back_returns_the_original(
    foreign_return: float, rate_before: float, rate_after: float
) -> None:
    home_return = convert(foreign_return, rate_before, rate_after)
    back = convert(home_return, 1 / rate_before, 1 / rate_after)
    assert back == pytest.approx(foreign_return, abs=1e-12)


@given(returns_strategy, rates_strategy, rates_strategy, st.floats(min_value=0.1, max_value=10.0))
def test_only_the_change_in_the_rate_matters(
    foreign_return: float, rate_before: float, rate_after: float, scale: float
) -> None:
    assert convert(foreign_return, rate_before * scale, rate_after * scale) == pytest.approx(
        convert(foreign_return, rate_before, rate_after), abs=1e-12
    )
