import math

import pytest

from crashmodel.data.gilts import (
    ALL_MATURITIES,
    OVER_15_YEARS,
    CurvePoints,
    gilt_models,
    ladder,
    short_gilts,
    stored_curve_points,
    zero_curves,
)
from crashmodel.data.models import IndexModel
from crashmodel.data.reference_data import FIVE_YEAR_PAR_YIELD, stored
from crashmodel.engine.curves import par_coupon
from crashmodel.engine.months import Month, MonthlySeries, month_range

START = Month(1982, 1)


def constant(value: float, start: Month = START, months: int = 24) -> MonthlySeries:
    return MonthlySeries(start, (value,) * months)


def points(twenty_from: Month = START + 6) -> CurvePoints:
    """Bank Rate at 3.65% (0.01% a day), yields at 4%, 5% and 6%; the 20-year point begins later."""
    return CurvePoints(
        overnight=constant(3.65, Month(1981, 1), 36),
        five_years=constant(4.0),
        ten_years=constant(5.0),
        twenty_years=constant(6.0, twenty_from, 24 - (twenty_from - START)),
    )


def test_the_all_maturities_ladder_holds_30_35_35_across_its_bands() -> None:
    def share(first: float, last: float) -> float:
        return sum(rung.weight for rung in ALL_MATURITIES if first <= rung.years_left <= last)

    assert len(ALL_MATURITIES) == 100
    assert (share(0.5, 5), share(5.5, 15), share(15.5, 50)) == pytest.approx((0.30, 0.35, 0.35))


def test_the_over_15_years_ladder_spreads_its_gilts_evenly_from_15_and_a_half_to_50() -> None:
    assert [rung.years_left for rung in OVER_15_YEARS] == [15.5 + k / 2 for k in range(70)]
    assert sum(rung.weight for rung in OVER_15_YEARS) == pytest.approx(1.0)


def test_curves_run_from_the_first_month_with_the_overnight_5_and_10_year_points() -> None:
    first, curves = zero_curves(points())
    assert first == START
    assert len(curves) == 24
    assert curves[0].yield_at(0) == pytest.approx(36500 * math.log(1.0001))


def test_until_the_20_year_point_begins_a_curve_stays_at_its_10_year_yield() -> None:
    _, curves = zero_curves(points())
    assert [curves[month].yield_at(20) for month in (5, 6)] == [5.0, 6.0]


def test_a_ladders_returns_start_the_month_after_the_20_year_point_begins() -> None:
    returns = ladder(ALL_MATURITIES, points(twenty_from=START + 6))
    assert (returns.start, returns.end) == (START + 7, START + 23)


def test_short_gilts_are_half_a_5_year_gilt_and_half_cash() -> None:
    """At an unchanged 6% the gilt earns 6/1200 = 0.5% a month, as does the cash here."""
    returns = short_gilts(constant(6.0), constant(0.005, START + 3, 10))
    assert (returns.start, returns.end) == (START + 3, START + 12)
    assert returns.values == pytest.approx((0.005,) * 10)


def test_the_three_gilt_models_are_built_together() -> None:
    models = gilt_models(points(), constant(6.0), constant(0.005))
    assert set(models) == {
        IndexModel.UK_GILTS_ALL,
        IndexModel.UK_GILTS_SHORT,
        IndexModel.UK_GILTS_LONG,
    }


def test_the_series_must_share_a_month() -> None:
    with pytest.raises(ValueError, match="share no month"):
        short_gilts(constant(6.0), constant(0.005, START + 30, 2))


def test_the_stored_zero_yields_are_continuously_compounded() -> None:
    """Read as continuously compounded, the stored curve's 5-year par coupon stays within 0.15
    points of the Bank's own 5-year par yield in every month; read as compounded half-yearly it
    would sit well below it at the high yields of the 1990s."""
    first, curves = zero_curves(stored_curve_points())
    by_month = dict(zip(month_range(first, first + (len(curves) - 1)), curves, strict=True))
    par_yields = stored(FIVE_YEAR_PAR_YIELD)
    gaps = [
        par_coupon(by_month[month], 5) - par_yields[month]
        for month in par_yields
        if month in by_month
    ]
    assert max(map(abs, gaps)) < 0.15
