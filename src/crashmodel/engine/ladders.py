"""A gilt index modelled as a ladder of gilts, each keeping the coupon it was issued with.

A gilt index holds gilts with every length of time left to run, and many of them were issued years
ago with coupons set by the yields of their day. When yields rise, a gilt with a high old coupon
falls less than a new low-coupon gilt with the same time left, because more of its value comes back
sooner. The ladder captures this:

- each rung is a time left to run, a whole number of half years, with a share of the gilts the
  ladder holds, counted at face value, as an index counts the amount of each gilt in issue;
- a rung holds equal amounts of gilts first issued at each of a few terms, those at least as long as
  the time left, and each pays the par coupon of the month it was issued (a gilt issued before the
  first curve takes that curve's coupon);
- each month every gilt is valued just after a coupon, off that month's zero curve, and again a
  month later, off the next month's curve, when every payment is a month nearer;
- the ladder's return is the change in the value of all its gilts, and each month it is filled
  again with the same amounts of each rung, so a rung whose gilts are worth more holds more of the
  money, as in an index.

Every payment falls on the half-year grid, so each month needs one discount factor per half year
on each curve, and running sums of them value every rung at once.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate

from crashmodel.engine.curves import COUPONS_PER_YEAR, PERCENT, ZeroCurve, par_coupon
from crashmodel.engine.months import MONTHS_IN_YEAR, Month, MonthlySeries

MINIMUM_CURVES = 2
"""A return needs the curve at both ends of a month."""


@dataclass(frozen=True)
class Rung:
    """Gilts with a given time left to run, and their share of the ladder's gilts at face value.

    Attributes:
        years_left: The time left to run, a whole number of half years.
        weight: Its share of the gilts the ladder holds, counted at face value, relative to the
            other rungs.
    """

    years_left: float
    weight: float

    def __post_init__(self) -> None:
        """Check that the rung is a whole number of half years and holds some gilts.

        Raises:
            ValueError: If it is not, or does not.
        """
        half_years = self.years_left * COUPONS_PER_YEAR
        if self.years_left <= 0 or half_years != round(half_years):
            raise ValueError(f"a rung must be a whole number of half years, not {self.years_left}")
        if self.weight <= 0:
            raise ValueError("a rung must hold some of the gilts")


@dataclass(frozen=True)
class _Holding:
    half_years: int
    issue_term: float
    months_since_issue: int
    amount: float


def ladder_returns(
    curves: Sequence[ZeroCurve], first: Month, rungs: Sequence[Rung], issue_terms: Sequence[float]
) -> MonthlySeries:
    """Return the ladder's monthly total returns.

    Args:
        curves: The zero curve at the end of each month from ``first``, with no gaps.
        first: The month of the first curve. Returns start the month after.
        rungs: The times left to run the ladder holds, and their shares of its gilts at face value.
        issue_terms: The terms, in years, that gilts are first issued at.

    Raises:
        ValueError: If there are fewer than two curves, there are no rungs, or a rung is longer than
            every issue term.
    """
    if len(curves) < MINIMUM_CURVES:
        raise ValueError("returns need curves for at least two months")
    if not rungs:
        raise ValueError("a ladder needs at least one rung")
    holdings = [holding for rung in rungs for holding in _holdings(rung, issue_terms)]
    coupons = {term: [par_coupon(curve, term) for curve in curves] for term in set(issue_terms)}
    longest = max(holding.half_years for holding in holdings)
    times = [k / COUPONS_PER_YEAR for k in range(1, longest + 1)]
    returns: list[float] = []
    for month in range(1, len(curves)):
        before, after = curves[month - 1], curves[month]
        now = [before.discount(time) for time in times]
        later = [after.discount(time - 1 / MONTHS_IN_YEAR) for time in times]
        annuity_now, annuity_later = list(accumulate(now)), list(accumulate(later))
        worth_before = worth_after = 0.0
        for holding in holdings:
            issued = max(month - 1 - holding.months_since_issue, 0)
            coupon = coupons[holding.issue_term][issued] / (COUPONS_PER_YEAR * PERCENT)
            last = holding.half_years - 1
            worth_before += holding.amount * (coupon * annuity_now[last] + now[last])
            worth_after += holding.amount * (coupon * annuity_later[last] + later[last])
        returns.append(worth_after / worth_before - 1)
    return MonthlySeries(first + 1, tuple(returns))


def _holdings(rung: Rung, issue_terms: Sequence[float]) -> list[_Holding]:
    """Split a rung's face value equally between the gilts issued for at least its time left."""
    terms = [term for term in issue_terms if term >= rung.years_left]
    if not terms:
        raise ValueError(f"no gilt is issued for long enough to have {rung.years_left} years left")
    return [
        _Holding(
            half_years=round(rung.years_left * COUPONS_PER_YEAR),
            issue_term=term,
            months_since_issue=round((term - rung.years_left) * MONTHS_IN_YEAR),
            amount=rung.weight / len(terms),
        )
        for term in terms
    ]
