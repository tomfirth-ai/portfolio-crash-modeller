import pytest

from crashmodel.app import stress
from crashmodel.app.splits import Slot, Split
from crashmodel.data.models import IndexModel
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import Episode
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import Rebalancing
from tests.app.example_funds import use_example_funds

EPISODE = Episode(key="test", start=Month(2007, 6), crash_end=Month(2007, 8), end=Month(2007, 9))
US_ONLY = Slot(split=Split(name="US", percentages={"sp500": 100}))
HALF_AND_HALF = Slot(split=Split(name="Half", percentages={"sp500": 50, "bank_rate": 50}))
CASH_ONLY = Slot(split=Split(name="Cash", percentages={"bank_rate": 100}))


def series(*values: float) -> MonthlySeries:
    return MonthlySeries(Month(2007, 7), values)


def panel(
    dollars: MonthlySeries | None = None, unavailable: frozenset[IndexModel] = frozenset()
) -> Panel:
    returns = {IndexModel.STERLING_CASH: series(0.0, 0.0, 0.0)}
    if IndexModel.US_LARGE not in unavailable:
        returns[IndexModel.US_LARGE] = series(-0.5, 1.0, 0.0)
    return Panel(
        returns=returns,
        unavailable=unavailable,
        vintages={},
        dollar_returns={} if dollars is None else {IndexModel.US_LARGE: dollars},
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
    assert outcome.drivers == {"sp500": -0.25, "bank_rate": 0.0}


def test_a_split_holding_shares_is_also_run_with_their_returns_in_dollars() -> None:
    [outcome] = stress.outcomes([US_ONLY], EPISODE, panel(series(-0.2, 0.0, 0.0)))
    assert outcome.shares_in_dollars is not None
    assert outcome.shares_in_dollars.fall is not None
    assert outcome.shares_in_dollars.fall.depth == pytest.approx(0.2)


def test_no_dollar_what_if_without_shares_or_their_full_dollar_history() -> None:
    short = MonthlySeries(Month(2007, 8), (0.0, 0.0))
    assert (
        stress.outcomes([CASH_ONLY], EPISODE, panel(series(0.0, 0.0, 0.0)))[0].shares_in_dollars
        is None
    )
    assert stress.outcomes([US_ONLY], EPISODE, panel(short))[0].shares_in_dollars is None


def test_a_split_whose_share_data_could_not_be_fetched_says_so() -> None:
    offline = panel(unavailable=frozenset({IndexModel.US_LARGE}))
    [outcome] = stress.outcomes([HALF_AND_HALF], EPISODE, offline)
    assert outcome.run is None
    assert (outcome.missing, outcome.fetch_failed) == (("sp500",), True)


def test_only_the_models_of_splits_that_will_run_are_loaded() -> None:
    left_out = Slot(split=Split(name="Off", percentages={"msci_world": 100}), included=False)
    unfinished = Slot(split=Split(name="Half done", percentages={"ftse_all_world": 50}))
    at_zero = Slot(split=Split(name="Zero", percentages={"bank_rate": 100, "uk_gilt": 0}))
    held = stress.models_held([US_ONLY, left_out, unfinished, at_zero])
    assert held == {IndexModel.US_LARGE, IndexModel.STERLING_CASH}


def test_holdings_without_data_are_named_once_each_in_the_order_they_appear() -> None:
    offline = panel(unavailable=frozenset({IndexModel.US_LARGE}))
    slots = [CASH_ONLY, HALF_AND_HALF, US_ONLY]
    assert stress.unavailable_holdings(slots, offline) == ["sp500"]
    assert stress.unavailable_holdings(slots, panel()) == []


@pytest.fixture
def example_funds(monkeypatch: pytest.MonkeyPatch) -> None:
    use_example_funds(monkeypatch)


def flat_shares(dollars: MonthlySeries) -> Panel:
    flat = series(0.0, 0.0, 0.0)
    return Panel(
        returns={IndexModel.US_LARGE: flat, IndexModel.STERLING_CASH: flat},
        unavailable=frozenset(),
        vintages={},
        dollar_returns={IndexModel.US_LARGE: dollars},
    )


@pytest.mark.usefixtures("example_funds")
def test_a_funds_charge_comes_off_its_returns_in_pounds_and_in_dollars() -> None:
    """A fund charging 0.1% a month keeps 0.999 of each month: flat in pounds, up 1% in dollars."""
    fund = Slot(split=Split(name="Fund", percentages={"late": 100}))
    [outcome] = stress.outcomes([fund], EPISODE, flat_shares(series(0.01, 0.01, 0.01)))
    assert outcome.run is not None
    assert outcome.shares_in_dollars is not None
    assert outcome.run.result.end_value == pytest.approx(100 * 0.999**3)
    assert outcome.shares_in_dollars.end_value == pytest.approx(100 * (1.01 * 0.999) ** 3)


@pytest.mark.usefixtures("example_funds")
def test_only_funds_held_and_launched_after_the_crash_began_are_launched_late() -> None:
    """The crash begins in June 2007: EARLY launched in May, START in June, LATE in August."""
    split = Split(
        name="Mixed", percentages={"early": 25, "start": 25, "late": 25, "sp500": 25, "later": 0}
    )
    [outcome] = stress.outcomes([Slot(split=split)], EPISODE, panel())
    assert outcome.launched_late == {"late": Month(2007, 8)}


@pytest.mark.usefixtures("example_funds")
def test_a_split_that_could_not_be_run_has_no_launch_months() -> None:
    offline = panel(unavailable=frozenset({IndexModel.US_LARGE}))
    late = Slot(split=Split(name="Late", percentages={"late": 100}))
    [outcome] = stress.outcomes([late], EPISODE, offline)
    assert (outcome.run, outcome.launched_late) == (None, {})
