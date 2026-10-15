import pytest

from crashmodel.engine.attribution import fall_contributions
from crashmodel.engine.drawdown import crash_result
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import Rebalancing, portfolio_path

START = Month(2020, 1)


def returns(*values: float) -> MonthlySeries:
    return MonthlySeries(START + 1, values)


def test_each_holdings_share_of_a_fall_adds_up_to_the_fall() -> None:
    """60% in shares that lose 40%, 40% in bonds that gain 10%.

    The split goes from 100 to 36 + 44 = 80: shares took off 24 and bonds added back 4.
    """
    path = portfolio_path(
        {"shares": 0.6, "bonds": 0.4},
        {"shares": returns(-0.4), "bonds": returns(0.1)},
        START,
        START + 1,
    )
    fall = crash_result(path.values, START + 1).fall
    assert fall is not None
    assert fall_contributions(path, fall) == pytest.approx({"shares": -0.24, "bonds": 0.04})


@pytest.mark.parametrize("rebalancing", list(Rebalancing))
def test_only_the_months_from_the_high_to_the_bottom_count(rebalancing: Rebalancing) -> None:
    """A rise to a new high comes first and a recovery after; neither is part of the fall."""
    shares, bonds = returns(0.10, -0.30, -0.10, 0.50), returns(0.00, 0.05, 0.05, 0.00)
    weights = {"shares": 0.5, "bonds": 0.5}
    path = portfolio_path(
        weights, {"shares": shares, "bonds": bonds}, START, START + 4, rebalancing
    )
    fall = crash_result(path.values, START + 3).fall
    assert fall is not None
    assert (fall.peak, fall.bottom) == (START + 1, START + 3)
    contributions = fall_contributions(path, fall)
    assert sum(contributions.values()) == pytest.approx(-fall.depth)
    assert contributions["shares"] < 0 < contributions["bonds"]
