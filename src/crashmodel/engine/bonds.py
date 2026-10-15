"""Monthly total returns of a 10-year government bond, from month-end yields.

Each month the bond held is a new 10-year bond bought at par, so its coupon equals that month's
yield. A month later it has 10 years less a month to run and is revalued at the new yield, and it
has earned a month of coupon. With yields y in percent, semi-annual coupons as for gilts, and
n = 2 * (10 - 1/12) half-years to run:

    r_t = y_{t-1} / 1200 + (y_{t-1} / y_t - 1) * (1 - (1 + y_t / 200) ** -n)

When yields rise the bond loses value, roughly by its duration (about 8 years) times the rise; when
they fall it gains a little more than it would lose on the same rise. This is the formula of
Swinkels' international government bond returns dataset (2023), https://doi.org/10.25397/eur.8152748,
whose method is described in Swinkels (2019), Data 4(3), 91, https://doi.org/10.3390/data4030091.
"""

from crashmodel.engine.months import MonthlySeries, month_range

MATURITY_YEARS = 10
MONTHS_IN_YEAR = 12
COUPONS_PER_YEAR = 2
PERCENT = 100
HALF_YEARS_TO_RUN = COUPONS_PER_YEAR * (MATURITY_YEARS - 1 / MONTHS_IN_YEAR)
"""Half-years a newly bought 10-year bond has left to run a month later."""
MINIMUM_MONTHS = 2
"""A return needs the yield at both ends of a month."""


def par_bond_returns(yields_percent: MonthlySeries) -> MonthlySeries:
    """Return monthly total returns of a 10-year par bond, from month-end yields in percent.

    The first month has no return: it is the month the first bond is bought.

    Raises:
        ValueError: If there are fewer than two months, or any yield is not positive, since the
            formula divides by the yield.
    """
    if len(yields_percent) < MINIMUM_MONTHS:
        raise ValueError("returns need yields for at least two months")
    if any(yield_percent <= 0 for yield_percent in yields_percent.values):
        raise ValueError("yields must be positive")
    return MonthlySeries.from_pairs(
        (month, _par_bond_return(yields_percent[month.previous], yields_percent[month]))
        for month in month_range(yields_percent.start + 1, yields_percent.end)
    )


def _par_bond_return(previous: float, current: float) -> float:
    discount: float = (1 + current / (COUPONS_PER_YEAR * PERCENT)) ** -HALF_YEARS_TO_RUN
    accrued = previous / (MONTHS_IN_YEAR * PERCENT)
    return accrued + (previous / current - 1) * (1 - discount)
