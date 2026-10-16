import pytest
from hypothesis import given
from hypothesis import strategies as st

from crashmodel.engine.indexes import SizedPortfolio, cap_weighted, largest_firms
from crashmodel.engine.months import Month, MonthlySeries

JANUARY = Month(2020, 1)
FEBRUARY = Month(2020, 2)
ROUNDING = 1e-12


def portfolio(
    returns: tuple[float, ...],
    firms: tuple[float, ...],
    size: tuple[float, ...],
    start: Month = JANUARY,
) -> SizedPortfolio:
    return SizedPortfolio(
        returns=MonthlySeries(start, returns),
        firms=MonthlySeries(start, firms),
        average_size=MonthlySeries(start, size),
    )


def test_portfolios_are_combined_in_proportion_to_their_market_value() -> None:
    """10 firms of size 3 are worth 30 and 7 of size 10 worth 70: (30 * 10% - 70 * 10%) / 100."""
    small = portfolio((0.10,), (10,), (3,))
    large = portfolio((-0.10,), (7,), (10,))
    assert cap_weighted([small, large]).values == pytest.approx((-0.04,))


def test_a_months_returns_are_weighted_by_that_months_values() -> None:
    """In February both are worth 50, so +20% and 0% average to +10%.

    January's values, 30 and 70, would give +6%: the values describe each portfolio at the start
    of the month whose returns they weight.
    """
    rising = portfolio((0.0, 0.20), (10, 10), (3, 5))
    steady = portfolio((0.0, 0.0), (7, 5), (10, 10))
    combined = cap_weighted([rising, steady])
    assert combined[FEBRUARY] == pytest.approx(0.10)
    assert combined[FEBRUARY] != pytest.approx(0.06)


def test_only_months_every_portfolio_covers_are_combined() -> None:
    first = portfolio((0.01, 0.02, 0.03), (1, 1, 1), (1, 1, 1))
    second = portfolio((0.01, 0.02, 0.03), (1, 1, 1), (1, 1, 1), start=FEBRUARY)
    combined = cap_weighted([first, second])
    assert (combined.start, combined.end) == (FEBRUARY, Month(2020, 3))
    assert combined.values == pytest.approx((0.015, 0.025))


def test_a_portfolio_with_no_firms_counts_for_nothing() -> None:
    empty = portfolio((-0.9999,), (0,), (0,))
    held = portfolio((0.05,), (4,), (2,))
    assert cap_weighted([empty, held]).values == pytest.approx((0.05,))


def test_the_largest_firms_are_taken_from_the_top_down() -> None:
    """Hi holds 2 firms worth 100 each, Mid 4 worth 25 each, Lo 10 worth 5 each.

    The largest 4 firms are Hi's 2 (worth 200) and 2 of Mid's 4 (worth 50):
    (200 * 1% + 50 * 2%) / 250 = 1.2%.
    """
    groups = [
        portfolio((0.01,), (2,), (100,)),
        portfolio((0.02,), (4,), (25,)),
        portfolio((0.04,), (10,), (5,)),
    ]
    assert largest_firms(groups, 4).values == pytest.approx((0.012,))
    assert largest_firms(groups, 2).values == pytest.approx((0.01,))
    # More firms than there are holds them all: (2 + 2 + 2) / 350.
    assert largest_firms(groups, 100).values == pytest.approx((6 / 350,))


def test_the_largest_firms_follow_the_firm_counts_month_by_month() -> None:
    """In January the largest 3 are Hi's 2 and one of Mid's: (200 * 1% + 25 * 2%) / 225.

    In February Hi holds 3 firms, so the largest 3 are all in Hi.
    """
    groups = [
        portfolio((0.01, 0.01), (2, 3), (100, 100)),
        portfolio((0.02, 0.02), (4, 4), (25, 25)),
    ]
    assert largest_firms(groups, 3).values == pytest.approx((2.5 / 225, 0.01))


@pytest.mark.parametrize("count", [0, -1])
def test_holding_no_firms_is_refused(count: int) -> None:
    with pytest.raises(ValueError, match="cannot hold"):
        largest_firms([portfolio((0.01,), (1,), (1,))], count)


@pytest.mark.parametrize(
    ("portfolios", "message"),
    [
        ([], "no portfolios"),
        (
            [
                portfolio((0.01,), (1,), (1,)),
                portfolio((0.01,), (1,), (1,), start=FEBRUARY),
            ],
            "no month in common",
        ),
        ([portfolio((0.01,), (0,), (5,))], "no portfolio has any market value"),
    ],
)
def test_combinations_that_mean_nothing_are_refused(
    portfolios: list[SizedPortfolio], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        cap_weighted(portfolios)


def test_a_portfolios_series_must_cover_the_same_months() -> None:
    with pytest.raises(ValueError, match="same months"):
        SizedPortfolio(
            returns=MonthlySeries(JANUARY, (0.01, 0.02)),
            firms=MonthlySeries(JANUARY, (1,)),
            average_size=MonthlySeries(JANUARY, (1, 1)),
        )


@pytest.mark.parametrize(("firms", "size"), [(-1.0, 1.0), (1.0, -1.0)])
def test_negative_counts_and_sizes_are_refused(firms: float, size: float) -> None:
    with pytest.raises(ValueError, match="negative"):
        portfolio((0.01,), (firms,), (size,))


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-0.5, max_value=0.5),
            st.integers(min_value=1, max_value=1000),
            st.floats(min_value=0.1, max_value=1000.0),
        ),
        min_size=1,
        max_size=6,
    )
)
def test_a_combination_lies_between_its_best_and_worst_portfolio(
    groups: list[tuple[float, int, float]],
) -> None:
    portfolios = [portfolio((r,), (float(n),), (size,)) for r, n, size in groups]
    [combined] = cap_weighted(portfolios).values
    returns = [r for r, _, _ in groups]
    assert min(returns) - ROUNDING <= combined <= max(returns) + ROUNDING
