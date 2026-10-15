import pytest

from crashmodel.app import stress
from crashmodel.app.splits import Slot, Split
from crashmodel.data.blocks import Block
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import Episode
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import Rebalancing

EPISODE = Episode(key="test", start=Month(2007, 6), crash_end=Month(2007, 8), end=Month(2007, 9))
US_ONLY = Slot(split=Split(name="US", percentages={Block.US_SHARES: 100}))
HALF_AND_HALF = Slot(split=Split(name="Half", percentages={Block.US_SHARES: 50, Block.CASH: 50}))


def series(*values: float) -> MonthlySeries:
    return MonthlySeries(Month(2007, 7), values)


def panel(dollars: MonthlySeries | None = None) -> Panel:
    returns = {Block.US_SHARES: series(-0.5, 1.0, 0.0), Block.CASH: series(0.0, 0.0, 0.0)}
    return Panel(
        returns=returns,
        unavailable=frozenset(),
        vintages={},
        dollar_returns={} if dollars is None else {Block.US_SHARES: dollars},
    )


def test_the_chosen_way_of_managing_each_split_reaches_the_engine() -> None:
    """Shares halve and then double: kept at its weights the split ends at 112.5, left alone 100."""
    ends = {
        rebalancing: stress.outcomes([HALF_AND_HALF], EPISODE, panel(), rebalancing)[0]
        for rebalancing in Rebalancing
    }
    assert {key: outcome.run and outcome.run.result.end_value for key, outcome in ends.items()} == {
        Rebalancing.MONTHLY: 112.5,
        Rebalancing.NEVER: 100.0,
    }


def test_a_split_that_fell_records_which_holdings_drove_the_fall() -> None:
    [outcome] = stress.outcomes([HALF_AND_HALF], EPISODE, panel())
    assert outcome.drivers == {Block.US_SHARES: -0.25, Block.CASH: 0.0}


def test_a_split_holding_shares_is_also_run_with_their_returns_in_dollars() -> None:
    [outcome] = stress.outcomes([US_ONLY], EPISODE, panel(series(-0.2, 0.0, 0.0)))
    assert outcome.shares_in_dollars is not None
    assert outcome.shares_in_dollars.fall is not None
    assert outcome.shares_in_dollars.fall.depth == pytest.approx(0.2)


def test_no_dollar_what_if_without_shares_or_their_full_dollar_history() -> None:
    cash_only = Slot(split=Split(name="Cash", percentages={Block.CASH: 100}))
    short = MonthlySeries(Month(2007, 8), (0.0, 0.0))
    assert (
        stress.outcomes([cash_only], EPISODE, panel(series(0.0, 0.0, 0.0)))[0].shares_in_dollars
        is None
    )
    assert stress.outcomes([US_ONLY], EPISODE, panel(short))[0].shares_in_dollars is None
