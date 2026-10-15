"""The return on cash that earns Bank Rate.

Interest accrues each calendar day at the rate in force that day, weekends and holidays included,
and is credited at the end of the month:

    r_month = sum over the month's days of (rate that day in percent) / 100 / 365

Bank Rate is the Bank of England's policy rate, not what a saver is actually paid, so this is a
yardstick for cash rather than any account's return.
"""

from collections.abc import Sequence
from datetime import date, timedelta
from itertools import pairwise

from crashmodel.engine.months import Month, MonthlySeries, month_range

DAYS_IN_YEAR = 365
"""The day count for sterling interest: a year is always 365 days, even in a leap year."""
PERCENT = 100


def monthly_cash_returns(observations: Sequence[tuple[date, float]], last: Month) -> MonthlySeries:
    """Return the monthly return on cash, from rates observed on working days.

    Args:
        observations: ``(day, annual rate in percent)`` pairs in date order. Each rate stays in
            force until the next observation.
        last: The last month to include. The observations must reach into it.

    Returns:
        Returns from the first month that has a rate in force on its first day, to ``last``.

    Raises:
        ValueError: If there are no observations, the days are out of order, or they do not
            cover every month up to ``last``.
    """
    if not observations:
        raise ValueError("there are no rate observations")
    days = [day for day, _ in observations]
    if any(later <= earlier for earlier, later in pairwise(days)):
        raise ValueError("observations must be in strictly increasing date order")
    first = Month.of(days[0]) if days[0].day == 1 else Month.of(days[0]) + 1
    if first > last or Month.of(days[-1]) < last:
        raise ValueError(f"the observations do not cover every month up to {last}")
    returns: list[tuple[Month, float]] = []
    current = 0
    for month in month_range(first, last):
        accrued = 0.0
        for offset in range(month.days):
            day = month.first_day + timedelta(days=offset)
            while current + 1 < len(observations) and days[current + 1] <= day:
                current += 1
            accrued += observations[current][1] / PERCENT / DAYS_IN_YEAR
        returns.append((month, accrued))
    return MonthlySeries.from_pairs(returns)
