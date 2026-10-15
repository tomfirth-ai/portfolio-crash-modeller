"""Exchange rates, and converting returns into the investor's own currency.

An investor in pounds who holds dollar shares earns two things: the shares' return in dollars, and
the change in the dollar's value against the pound. When the pound falls, the dollars are worth more
pounds, which cushions a sterling investor in a global crash. Both effects multiply:

    r_home = (1 + r_foreign) * X[t-1] / X[t] - 1

where X is the exchange rate quoted as foreign currency per unit of home currency (US dollars per
pound). Adding the two returns instead drops their product, which is large in a crash: a 50% fall in
dollars while the pound halves leaves a sterling investor exactly where they started.
"""

from collections.abc import Iterable
from datetime import date
from itertools import pairwise

from crashmodel.engine.months import Month, MonthlySeries


def month_end_rates(observations: Iterable[tuple[date, float]]) -> MonthlySeries:
    """Return the last observation in each calendar month.

    Args:
        observations: ``(day, rate)`` pairs in date order, leaving out days with no rate.

    Raises:
        ValueError: If the days are out of order, or a whole month has no observation.
    """
    last_in_month: dict[Month, float] = {}
    previous: date | None = None
    for day, rate in observations:
        if previous is not None and day <= previous:
            raise ValueError(f"observations must be in date order: {day} follows {previous}")
        last_in_month[Month.of(day)] = rate
        previous = day
    return MonthlySeries.from_pairs(last_in_month.items())


def to_home_currency(returns: MonthlySeries, foreign_per_home: MonthlySeries) -> MonthlySeries:
    """Convert monthly returns earned in a foreign currency into the home currency.

    Args:
        returns: Monthly returns in the foreign currency, as decimals (0.05 is 5%).
        foreign_per_home: Month-end exchange rates, in foreign currency per unit of home currency.

    Returns:
        Home-currency returns for every month that has a return and a rate at both of its ends.

    Raises:
        ValueError: If no month has both.
    """
    first = max(returns.start, foreign_per_home.start + 1)
    last = min(returns.end, foreign_per_home.end)
    if first > last:
        raise ValueError("the returns and the exchange rates have no month in common")
    foreign = returns.between(first, last).values
    rates = pairwise(foreign_per_home.between(first.previous, last).values)
    return MonthlySeries(
        first,
        tuple(
            (1 + r) * before / after - 1 for r, (before, after) in zip(foreign, rates, strict=True)
        ),
    )
