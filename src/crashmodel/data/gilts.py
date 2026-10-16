"""The UK gilt models, built from the Bank of England series stored with the app (ADR 0006).

- *All maturities* and *over 15 years* are ladders of gilts that keep their coupons, priced off
  each month's zero curve: Bank Rate at term zero and the Bank's 5, 10 and 20-year zero yields.
- *Up to 5 years* is half a 5-year gilt bought new each month at the 5-year par yield and half cash
  earning SONIA, put back to half and half each month.

Curves run from January 1982, when the 5 and 10-year yields begin, so that gilts issued since then
take the coupon of their own issue month; until the 20-year yield begins in March 1992 a curve
stays at its 10-year yield beyond 10 years. The ladders' returns start once the curve reaches
20 years. The terms and shares describe the indexes' usual shape; none was fitted to an index's
returns.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from crashmodel.data.models import IndexModel
from crashmodel.data.reference_data import (
    FIVE_YEAR_ZERO_YIELD,
    MONTH_END_BANK_RATE,
    TEN_YEAR_ZERO_YIELD,
    TWENTY_YEAR_ZERO_YIELD,
    stored,
)
from crashmodel.engine.bonds import par_bond_returns
from crashmodel.engine.curves import ZeroCurve, continuous_overnight_rate
from crashmodel.engine.ladders import Rung, ladder_returns
from crashmodel.engine.months import Month, MonthlySeries, month_range

ISSUE_TERMS = (5, 10, 30, 50)
"""The terms, in years, that gilts in the ladders were first issued at."""
HALF_YEARS_PER_YEAR = 2


def _band(first: float, last: float, share: float) -> list[Rung]:
    """Rungs every half year from ``first`` to ``last`` years, holding ``share`` of the gilts."""
    count = round((last - first) * HALF_YEARS_PER_YEAR) + 1
    return [Rung(first + step / HALF_YEARS_PER_YEAR, share / count) for step in range(count)]


ALL_MATURITIES = (*_band(0.5, 5, 0.30), *_band(5.5, 15, 0.35), *_band(15.5, 50, 0.35))
"""Up to 5 years left: 30% of the gilts at face value; 5 to 15 years: 35%; over 15 years: 35%."""
OVER_15_YEARS = tuple(_band(15.5, 50, 1.0))
SHORT_GILT_YEARS = 5
SHORT_GILT_SHARE = 0.5
"""The up-to-5-years model holds half its money in a 5-year gilt and half in cash."""


@dataclass(frozen=True, kw_only=True)
class CurvePoints:
    """The month-end series a zero curve is drawn through, yields in percent.

    Attributes:
        overnight: The overnight rate, for term zero.
        five_years: The 5-year zero-coupon yield.
        ten_years: The 10-year zero-coupon yield.
        twenty_years: The 20-year zero-coupon yield, which may begin later than the others.
    """

    overnight: MonthlySeries
    five_years: MonthlySeries
    ten_years: MonthlySeries
    twenty_years: MonthlySeries


def stored_curve_points() -> CurvePoints:
    """The curve's points from the series stored with the app."""
    return CurvePoints(
        overnight=stored(MONTH_END_BANK_RATE),
        five_years=stored(FIVE_YEAR_ZERO_YIELD),
        ten_years=stored(TEN_YEAR_ZERO_YIELD),
        twenty_years=stored(TWENTY_YEAR_ZERO_YIELD),
    )


def zero_curves(points: CurvePoints) -> tuple[Month, list[ZeroCurve]]:
    """Return each month's zero curve, and the first month, over the months its points cover.

    The 20-year point joins the curve in the months it covers.

    Raises:
        ValueError: If the overnight, 5 and 10-year series share no month.
    """
    first, last = _common_months([points.overnight, points.five_years, points.ten_years])
    twenty = points.twenty_years
    curves = [
        ZeroCurve.from_points(
            {
                0: continuous_overnight_rate(points.overnight[month]),
                5: points.five_years[month],
                10: points.ten_years[month],
                **({20: twenty[month]} if twenty.start <= month <= twenty.end else {}),
            }
        )
        for month in month_range(first, last)
    ]
    return first, curves


def ladder(rungs: Sequence[Rung], points: CurvePoints) -> MonthlySeries:
    """Return a ladder's monthly returns, from the month after the 20-year point begins.

    The ladder runs over every curve, so that each gilt takes the coupon of its own issue month,
    and is then cut to the months whose curves reach 20 years at both ends.
    """
    first, curves = zero_curves(points)
    returns = ladder_returns(curves, first, rungs, ISSUE_TERMS)
    return returns.between(
        max(returns.start, points.twenty_years.start + 1),
        min(returns.end, points.twenty_years.end),
    )


def short_gilts(five_year_par_yield: MonthlySeries, cash: MonthlySeries) -> MonthlySeries:
    """Return half a new 5-year gilt and half cash each month, put back to half and half."""
    gilt = par_bond_returns(five_year_par_yield, SHORT_GILT_YEARS)
    first, last = _common_months([gilt, cash])
    return MonthlySeries.from_pairs(
        (month, SHORT_GILT_SHARE * gilt[month] + (1 - SHORT_GILT_SHARE) * cash[month])
        for month in month_range(first, last)
    )


def gilt_models(
    points: CurvePoints, five_year_par_yield: MonthlySeries, cash: MonthlySeries
) -> dict[IndexModel, MonthlySeries]:
    """Return the monthly returns of the three gilt models."""
    return {
        IndexModel.UK_GILTS_ALL: ladder(ALL_MATURITIES, points),
        IndexModel.UK_GILTS_SHORT: short_gilts(five_year_par_yield, cash),
        IndexModel.UK_GILTS_LONG: ladder(OVER_15_YEARS, points),
    }


def _common_months(series: Sequence[MonthlySeries]) -> tuple[Month, Month]:
    first, last = max(s.start for s in series), min(s.end for s in series)
    if first > last:
        raise ValueError("the series share no month")
    return first, last
