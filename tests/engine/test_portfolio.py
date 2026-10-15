import pytest

from crashmodel.engine.currency import to_home_currency
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import STARTING_VALUE, rebalanced_values

START = Month(2020, 1)


def series(*returns: float) -> MonthlySeries:
    return MonthlySeries(START + 1, returns)


def values(
    weights: dict[str, float], returns: dict[str, MonthlySeries], months: int
) -> list[float]:
    return list(rebalanced_values(weights, returns, START, START + months).values)


def test_a_split_starts_at_100_at_the_end_of_its_first_month() -> None:
    path = rebalanced_values({"cash": 1.0}, {"cash": series(0.0)}, START, START + 1)
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


def test_a_split_of_one_holding_follows_that_holding() -> None:
    assert values({"shares": 1.0}, {"shares": series(0.10, -0.50)}, 2) == pytest.approx(
        [100, 110, 55]
    )


def test_holdings_with_no_weight_need_no_returns() -> None:
    assert values({"shares": 1.0, "bonds": 0.0}, {"shares": series(0.10)}, 1) == pytest.approx(
        [100, 110]
    )


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


def test_the_last_month_cannot_come_before_the_first() -> None:
    with pytest.raises(ValueError, match="before"):
        rebalanced_values({"cash": 1.0}, {"cash": series(0.0)}, START, START + -1)
