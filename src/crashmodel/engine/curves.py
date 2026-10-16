"""Zero-coupon yield curves: what a pound due at a future date is worth today.

A zero-coupon yield is the annual rate, continuously compounded and in percent, at which a single
payment due at a given term is discounted, so a pound due in ``t`` years is worth

    D(t) = exp(-z(t) / 100 * t)

today. The Bank of England publishes its estimate of the gilt curve at a few terms; between them the
curve is drawn as straight lines, and beyond the first and last it stays flat. A gilt is a set of
such payments: a coupon every half year and its face value at the end. Its par coupon is the one
that makes it worth its face value:

    c = 200 * (1 - D(T)) / (D(0.5) + D(1) + ... + D(T))    (percent a year, paid half-yearly)
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import Self

PERCENT = 100
COUPONS_PER_YEAR = 2
DAYS_IN_YEAR = 365
"""The day count of sterling overnight rates."""


@dataclass(frozen=True)
class ZeroCurve:
    """A zero-coupon yield curve, known at a few terms.

    Attributes:
        points: ``(term in years, yield in percent)`` pairs, shortest term first.
    """

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        """Check that the curve has points at distinct terms, in order, none of them negative.

        Raises:
            ValueError: If it does not.
        """
        if not self.points:
            raise ValueError("a curve needs at least one point")
        terms = [term for term, _ in self.points]
        if terms[0] < 0 or any(later <= earlier for earlier, later in pairwise(terms)):
            raise ValueError("terms must be zero or more, and strictly increasing")

    @classmethod
    def from_points(cls, points: Mapping[float, float]) -> Self:
        """Build a curve from yields keyed by term in years, in any order."""
        return cls(tuple(sorted(points.items())))

    def yield_at(self, term: float) -> float:
        """The yield at ``term`` years: on a straight line between points, flat beyond them."""
        first_term, first_yield = self.points[0]
        if term <= first_term:
            return first_yield
        for (earlier, earlier_yield), (later, later_yield) in pairwise(self.points):
            if term <= later:
                share = (term - earlier) / (later - earlier)
                return earlier_yield + share * (later_yield - earlier_yield)
        return self.points[-1][1]

    def discount(self, term: float) -> float:
        """What a pound due in ``term`` years is worth today."""
        return math.exp(-self.yield_at(term) / PERCENT * term)


def continuous_overnight_rate(rate_percent: float) -> float:
    """The continuously compounded rate, in percent, that earns what an overnight rate does.

    An overnight rate such as SONIA earns ``rate / 100 / 365`` a day, compounded daily, so it is
    worth ``365 * ln(1 + rate / 100 / 365)`` a year continuously compounded: a little less than
    the rate itself.
    """
    return DAYS_IN_YEAR * math.log1p(rate_percent / PERCENT / DAYS_IN_YEAR) * PERCENT


def par_coupon(curve: ZeroCurve, term_years: float) -> float:
    """The coupon, in percent a year paid half-yearly, that makes a new gilt worth its face value.

    Raises:
        ValueError: If the term is not a positive whole number of half years.
    """
    half_years = term_years * COUPONS_PER_YEAR
    if term_years <= 0 or half_years != round(half_years):
        raise ValueError(f"a gilt's term must be a whole number of half years, not {term_years}")
    discounts = [curve.discount(k / COUPONS_PER_YEAR) for k in range(1, round(half_years) + 1)]
    return COUPONS_PER_YEAR * PERCENT * (1 - discounts[-1]) / sum(discounts)
