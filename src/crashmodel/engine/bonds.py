"""Monthly total returns of a government bond bought new each month, from month-end par yields.

Each month the bond held is a new bond of a fixed term bought at par, so its coupon equals that
month's yield. A month later it has a month less to run and is revalued at the new yield, and it
has earned a month of coupon. With yields y in percent, semi-annual coupons as for gilts, and
n = 2 * (term - 1/12) half-years to run:

    r_t = y_{t-1} / 1200 + (y_{t-1} - y_t) * A(y_t),    A(y) = (1 - (1 + y / 200) ** -n) / y

When yields rise the bond loses value, roughly by its duration times the rise; when they fall it
gains a little more than it would lose on the same rise. This is the formula of Swinkels'
international government bond returns dataset (2023), https://doi.org/10.25397/eur.8152748, whose
method is described in Swinkels (2019), Data 4(3), 91, https://doi.org/10.3390/data4030091. It is
written here with the annuity factor A, which has the value n / 200 when the yield is zero, so the
formula also holds at zero and negative yields, as some gilt yields were in 2020.
"""

import math
from itertools import pairwise

from crashmodel.engine.months import MONTHS_IN_YEAR, MonthlySeries

COUPONS_PER_YEAR = 2
PERCENT = 100
LOWEST_YIELD = -COUPONS_PER_YEAR * PERCENT
"""A yield at or below -200% would make the half-yearly discount factor meaningless."""
MINIMUM_MONTHS = 2
"""A return needs the yield at both ends of a month."""


def par_bond_returns(yields_percent: MonthlySeries, term_years: float) -> MonthlySeries:
    """Return monthly total returns of a par bond of a given term, from month-end yields in percent.

    The first month has no return: it is the month the first bond is bought.

    Raises:
        ValueError: If there are fewer than two months, the term is not longer than a month, or a
            yield is -200% or lower.
    """
    if len(yields_percent) < MINIMUM_MONTHS:
        raise ValueError("returns need yields for at least two months")
    half_years = COUPONS_PER_YEAR * (term_years - 1 / MONTHS_IN_YEAR)
    if half_years <= 0:
        raise ValueError(f"a {term_years}-year bond has no time left to run a month later")
    if any(yield_percent <= LOWEST_YIELD for yield_percent in yields_percent.values):
        raise ValueError(f"yields must be above {LOWEST_YIELD}%")
    return MonthlySeries(
        yields_percent.start + 1,
        tuple(
            previous / (MONTHS_IN_YEAR * PERCENT)
            + (previous - current) * _annuity_factor(current, half_years)
            for previous, current in pairwise(yields_percent.values)
        ),
    )


def _annuity_factor(yield_percent: float, half_years: float) -> float:
    """``(1 - (1 + y / 200) ** -n) / y``, and its limit ``n / 200`` at a zero yield."""
    if yield_percent == 0:
        return half_years / (COUPONS_PER_YEAR * PERCENT)
    growth = math.log1p(yield_percent / (COUPONS_PER_YEAR * PERCENT))
    return -math.expm1(-half_years * growth) / yield_percent
