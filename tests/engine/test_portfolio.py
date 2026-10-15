import pytest

from crashmodel.engine.currency import to_home_currency
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import STARTING_VALUE, Rebalancing, portfolio_path

START = Month(2020, 1)


def series(*returns: float) -> MonthlySeries:
    return MonthlySeries(START + 1, returns)


def values(
    weights: dict[str, float],
    returns: dict[str, MonthlySeries],
    months: int,
    rebalancing: Rebalancing = Rebalancing.MONTHLY,
) -> list[float]:
    return list(portfolio_path(weights, returns, START, START + months, rebalancing).values.values)


def test_a_split_starts_at_100_at_the_end_of_its_first_month() -> None:
    path = portfolio_path({"cash": 1.0}, {"cash": series(0.0)}, START, START + 1).values
    assert (path.start, path[START]) == (START, STARTING_VALUE)


@pytest.mark.parametrize(
    ("shares", "expected"),
    [
        ((-0.50, 1.00), [100, 75, 112.5]),  # a V-shaped crash: rebalancing buys shares cheap
        ((-0.50, -0.50), [100, 75, 56.25]),  # a fall that continues: rebalancing keeps buying
    ],
)
def test_a_half_and_half_split_is_rebalanced_every_month(
    shares: tuple[float, float], expected: list[float]
) -> None:
    returns = {"shares": series(*shares), "cash": series(0.0, 0.0)}
    assert values({"shares": 0.5, "cash": 0.5}, returns, 2) == pytest.approx(expected)


def test_sixty_forty_falls_by_the_weighted_return() -> None:
    returns = {"shares": series(-0.40), "bonds": series(0.0)}
    assert values({"shares": 0.6, "bonds": 0.4}, returns, 1) == pytest.approx([100, 76])


@pytest.mark.parametrize("rebalancing", list(Rebalancing))
def test_a_split_of_one_holding_follows_that_holding(rebalancing: Rebalancing) -> None:
    returns = {"shares": series(0.10, -0.50)}
    assert values({"shares": 1.0}, returns, 2, rebalancing) == pytest.approx([100, 110, 55])


@pytest.mark.parametrize("rebalancing", list(Rebalancing))
def test_holdings_with_no_weight_need_no_returns(rebalancing: Rebalancing) -> None:
    weights, returns = {"shares": 1.0, "bonds": 0.0}, {"shares": series(0.10)}
    assert values(weights, returns, 1, rebalancing) == pytest.approx([100, 110])


def test_sterling_shares_and_cash_through_a_crash_and_a_falling_pound() -> None:
    dollars_per_pound = MonthlySeries(START, (2.0, 2.0, 1.0))
    us_shares = to_home_currency(series(-0.50, 0.0), dollars_per_pound)
    returns = {"us shares": us_shares, "cash": series(0.0, 0.0)}
    assert values({"us shares": 0.6, "cash": 0.4}, returns, 2) == pytest.approx([100, 70, 112])


@pytest.mark.parametrize(
    ("weights", "message"),
    [
        ({"shares": 1.2, "cash": -0.2}, "negative"),
        ({"shares": 0.6, "cash": 0.3}, "add up to 1"),
    ],
)
def test_weights_must_be_a_real_split(weights: dict[str, float], message: str) -> None:
    returns = {"shares": series(0.0), "cash": series(0.0)}
    with pytest.raises(ValueError, match=message):
        values(weights, returns, 1)


def test_every_held_holding_needs_returns_for_every_month() -> None:
    with pytest.raises(ValueError, match="no returns"):
        values({"shares": 1.0}, {"shares": series(0.1)}, 2)
    with pytest.raises(ValueError, match="no returns"):
        values({"bonds": 1.0}, {"shares": series(0.1)}, 1)


@pytest.mark.parametrize("months", [0, -1])
def test_the_last_month_must_come_after_the_first(months: int) -> None:
    with pytest.raises(ValueError, match="is not after"):
        portfolio_path({"cash": 1.0}, {"cash": series(0.0)}, START, START + months)


HALF_AND_HALF = {"shares": 0.5, "cash": 0.5}
V_SHAPE = {"shares": series(-0.50, 1.00), "cash": series(0.0, 0.0)}


def test_a_split_left_alone_lets_its_weights_drift() -> None:
    """Shares halve and then double: left alone, the split is back where it started.

    Kept at its weights, it would have bought more shares after the fall and ended at 112.5.
    """
    path = portfolio_path(HALF_AND_HALF, V_SHAPE, START, START + 2, Rebalancing.NEVER)
    assert path.values.values == pytest.approx((100, 75, 100))
    assert path.gains["shares"].values == pytest.approx((-25, 25))
    assert path.gains["cash"].values == pytest.approx((0, 0))


def test_rebalancing_puts_the_split_back_to_its_weights_before_each_month() -> None:
    path = portfolio_path(HALF_AND_HALF, V_SHAPE, START, START + 2, Rebalancing.MONTHLY)
    assert path.gains["shares"].values == pytest.approx((-25, 37.5))


@pytest.mark.parametrize("rebalancing", list(Rebalancing))
def test_each_months_gains_add_up_to_the_change_in_value(rebalancing: Rebalancing) -> None:
    returns = {"shares": series(-0.3, 0.2, 0.05), "bonds": series(0.02, -0.01, 0.03)}
    path = portfolio_path({"shares": 0.7, "bonds": 0.3}, returns, START, START + 3, rebalancing)
    for month, value in list(path.values.items())[1:]:
        gained = sum(gains[month] for gains in path.gains.values())
        assert gained == pytest.approx(value - path.values[month.previous])


def test_three_holdings_left_alone_each_grow_on_their_own() -> None:
    """50 in shares, 30 in bonds and 20 in cash, never touched.

    Each amount just compounds: shares 50 x 0.8 x 1.25 x 1.1 = 55, bonds 30 x 1.1 x 0.9 x 1.0
    = 29.7 and cash 20 x 1.05 x 1.05 x 1.05 = 23.1525, so the split ends at 107.8525.
    """
    returns = {
        "shares": series(-0.20, 0.25, 0.10),
        "bonds": series(0.10, -0.10, 0.00),
        "cash": series(0.05, 0.05, 0.05),
    }
    weights = {"shares": 0.5, "bonds": 0.3, "cash": 0.2}
    path = portfolio_path(weights, returns, START, START + 3, Rebalancing.NEVER)
    assert path.values.values == pytest.approx((100, 94, 101.75, 107.8525))
    assert sum(path.gains["shares"].values) == pytest.approx(5)
    assert sum(path.gains["bonds"].values) == pytest.approx(-0.3)
    assert sum(path.gains["cash"].values) == pytest.approx(3.1525)
